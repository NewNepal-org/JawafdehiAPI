"""
AgniService implementation for document processing and entity extraction.

Provides the AgniService orchestration layer that coordinates between
GenAI services, search services, and persistence for the Jawafdehi platform.
"""

import logging
from typing import Optional, Any
from pathlib import Path

from .genai import GenAIService, create_genai_service
from .persistence import PersistenceService, create_persistence_service
from .search import create_search_service, SearchService

from .agni_models import (
    ConversationKey,
    EntityMatchState,
    MessageAuthorType,
    EntityChange,
    AgniExtractionSession,
    ResolutionStatus,
)

logger = logging.getLogger(__name__)


class AgniServiceError(Exception):
    """Exception raised when AgniService operations fail."""
    pass


class AgniService:
    """
    Orchestrates entity extraction and resolution pipeline.
    
    This service coordinates between GenAI, search, and persistence services
    to provide the complete Agni workflow for document processing.
    """
    
    def __init__(self, search: SearchService, genai: GenAIService, persistence: PersistenceService):
        """
        Initialize AgniService with service dependencies.
        
        Args:
            search: Search service for entity matching and resolution (required)
            genai: GenAI service for AI-powered extraction (required)
            persistence: Persistence service for queuing and applying changes (required)
        """
        if not search:
            raise ValueError("Search service is required")
        if not genai:
            raise ValueError("GenAI service is required")
        if not persistence:
            raise ValueError("Persistence service is required")
            
        self.search = search
        self.genai = genai
        self.persistence = persistence
    
    def create_session(self, guidance: Optional[str] = None) -> AgniExtractionSession:
        """Create a new extraction session.
        
        Args:
            guidance: Optional guidance text to steer AI extraction behavior
            
        Returns:
            New AgniExtractionSession instance
        """
        session = AgniExtractionSession(guidance=guidance)
        logger.debug("Created new extraction session")
        return session
    
    def add_message(
        self, 
        session: AgniExtractionSession, 
        message_text: str, 
        conversation_type: str = "general",
        entity_id: Optional[int] = None
    ) -> None:
        """
        Add user message to the session conversation.
        
        Args:
            session: AgniExtractionSession to add message to
            message_text: User message text
            conversation_type: Type of conversation ("metadata", "entities", "entity")
            entity_id: Entity ID for entity-specific conversation
        """
        if conversation_type == "metadata":
            conversation = session.get_conversation(ConversationKey.METADATA_EXTRACTION)
        elif conversation_type == "entities":
            conversation = session.get_conversation(ConversationKey.ENTITY_EXTRACTION)
        elif conversation_type == "entity" and entity_id is not None:
            conversation = session.get_conversation(ConversationKey.entity(entity_id))
        else:
            # Default to entity extraction conversation
            conversation = session.get_conversation(ConversationKey.ENTITY_EXTRACTION)
        
        conversation.add(MessageAuthorType.USER, message_text)
        logger.debug(f"Added {conversation_type} message to session")
    
    async def ai_background_research(self, session) -> AgniExtractionSession:
        """
        Extract document metadata and entities using AI.
        
        Stage 1 of the two-stage extraction flow:
        - Extracts document metadata (title, author, date, etc.)
        - Returns a list of resolved entities identified in the document
        - Fast, single LLM call for the entire document
        
        Args:
            session: AgniExtractionSession instance
            
        Returns:
            Updated AgniExtractionSession with metadata and entities populated
            
        Raises:
            AgniServiceError: If the extraction fails
        """
        if session.source_document is None:
            raise ValueError("No document provided")
        
        try:
            session.metadata, session.entities = await self.genai.extract_metadata(
                session.source_document, session
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Error in ai_background_research: {e}")
            raise AgniServiceError(f"Background research failed: {str(e)}")

    async def ai_resolve_entity(self, session: AgniExtractionSession, entity_id: str) -> EntityMatchState:
        """
        Resolve a specific entity to NES matches.
        
        Stage 2 of the two-stage extraction flow:
        - Resolves the entity with the given unique identifier to NES matches
        - Searches for existing NES matches
        - Can be called per-entity, enabling incremental processing and user feedback
        
        Args:
            session: AgniExtractionSession with extracted entities
            entity_id: Unique identifier of the entity to resolve
            
        Returns:
            The resolved EntityMatchState with candidates populated
            
        Raises:
            AgniServiceError: If the resolution fails
            ValueError: If entity not found
        """
        try:
            entity = self._get_entity_by_id(session, entity_id)
            await self._resolve_single_entity(session, entity)
            return entity
            
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Error in ai_resolve_entity: {e}")
            raise AgniServiceError(f"Entity resolution failed: {str(e)}")

    def _get_entity_by_id(self, session: AgniExtractionSession, entity_id: str) -> EntityMatchState:
        """
        Get entity by ID from session.
        
        Args:
            session: AgniExtractionSession instance
            entity_id: Entity ID to find
            
        Returns:
            EntityMatchState
            
        Raises:
            ValueError: If entity not found
        """
        entity = next(
            (e for e in session.entities if e.entity_id == entity_id),
            None
        )
        if entity is None:
            raise ValueError(f"Entity not found: {entity_id}")
        return entity

    async def resolve_entities(self, session: AgniExtractionSession) -> AgniExtractionSession:
        """
        Resolve all entities to NES matches or mark for creation.
        
        Batch resolution of all entities in the session. This is a convenience
        method that calls ai_resolve_entity for each entity.
        
        Args:
            session: AgniExtractionSession with extracted entities
            
        Returns:
            Updated AgniExtractionSession with entity candidates populated
            
        Raises:
            AgniServiceError: If the resolution fails
        """
        try:
            for entity in session.entities:
                await self._resolve_single_entity(session, entity)
            
            return session
            
        except Exception as e:
            logger.error(f"Error in resolve_entities: {e}")
            raise AgniServiceError(f"Entity resolution failed: {str(e)}")

    async def _resolve_single_entity(
        self, session: AgniExtractionSession, entity: EntityMatchState
    ) -> None:
        """
        Internal method to resolve a single entity.
        
        Searches for NES candidates, then uses GenAI to:
        1. Score each candidate's match confidence based on document context
        2. Generate proposed_changes diff for the entity
        
        Args:
            session: AgniExtractionSession with document metadata for context
            entity: EntityMatchState to resolve
        """
        entity.candidates = self.search.find_matches(entity)

        if len(entity.candidates) == 0:
            logger.debug(f"No matches found for entity {entity.entity_id}")

        # Use GenAI to evaluate candidates and compute proposed changes
        scored_candidates, proposed_changes = await self.genai.resolve_entity_candidates(
            entity=entity,
            metadata=session.metadata,
        )
        
        entity.candidates = scored_candidates
        entity.proposed_changes = proposed_changes
        
        # Auto-match high confidence candidates
        if entity.candidates and entity.candidates[0].confidence and entity.candidates[0].confidence > 0.9:
            entity.matched_nes_id = entity.candidates[0].nes_id
            entity.resolution_status = ResolutionStatus.MATCHED
        elif not entity.candidates:
            entity.needs_creation = True
            entity.resolution_status = ResolutionStatus.CREATE_NEW
        else:
            entity.resolution_status = ResolutionStatus.NEEDS_REVIEW
    
    async def update_entity(self, session, entity_index: int, message: str) -> Any:
        """
        Update a specific entity based on user conversation.
        
        Args:
            session: AgniExtractionSession instance
            entity_index: Index of the entity to update
            message: User message for entity update
            
        Returns:
            Updated AgniExtractionSession with entity updated
            
        Raises:
            AgniServiceError: If the update fails
        """
        try:
            # Add user message to entity conversation
            conversation_key = ConversationKey.entity(entity_index)
            conversation = session.get_conversation(conversation_key)
            conversation.add(MessageAuthorType.USER, message)
            
            # Use GenAI service to process the conversation
            updated_entity = await self.genai.update_entity(
                session.entities[entity_index], session, conversation
            )
            session.entities[entity_index] = updated_entity
            
            return session
            
        except Exception as e:
            logger.error(f"Error in update_entity: {e}")
            raise AgniServiceError(f"Entity update failed: {str(e)}")
    
    def persist(self, session: AgniExtractionSession, description: str, author_id: str) -> Any:
        """
        Persist all extracted entities. All entities must be resolved.
        
        Args:
            session: AgniExtractionSession instance
            description: Description of the changes
            author_id: ID of the user approving the changes
            
        Returns:
            Updated AgniExtractionSession
            
        Raises:
            AgniServiceError: If persistence fails
        """
        try:
            for i, entity in enumerate(session.entities):
                # Skip entities marked as skipped
                if entity.resolution_status == ResolutionStatus.SKIPPED:
                    continue
                
                if entity.resolution_status not in (
                    ResolutionStatus.MATCHED,
                    ResolutionStatus.CREATE_NEW
                ):
                    raise ValueError(
                        f"Entity {i} has status '{entity.resolution_status.value}', "
                        "must be 'matched' or 'create_new'"
                    )
                
                change = EntityChange(
                    entity_type=entity.entity_type,
                    entity_subtype=entity.entity_subtype,
                    entity_data=entity.proposed_changes,
                    entity_id=entity.matched_nes_id if entity.resolution_status == ResolutionStatus.MATCHED else None,
                    change_type='update' if entity.resolution_status == ResolutionStatus.MATCHED else 'create',
                )
                
                self.persistence.queue_entity_change(change, description, author_id)
            
            return session
            
        except Exception as e:
            logger.error(f"Error in persist: {e}")
            raise AgniServiceError(f"Persistence failed: {str(e)}")

    def get_progress_info(self, session: AgniExtractionSession) -> dict:
        """
        Get progress information for a session.
        
        Args:
            session: AgniExtractionSession instance
            
        Returns:
            Dict with entity counts by resolution status
        """
        return {
            'total_entities': len(session.entities),
            'needs_review': sum(
                1 for e in session.entities
                if e.resolution_status == ResolutionStatus.NEEDS_REVIEW
            ),
            'matched': sum(
                1 for e in session.entities
                if e.resolution_status == ResolutionStatus.MATCHED
            ),
            'create_new': sum(
                1 for e in session.entities
                if e.resolution_status == ResolutionStatus.CREATE_NEW
            ),
            'skipped': sum(
                1 for e in session.entities
                if e.resolution_status == ResolutionStatus.SKIPPED
            ),
        }

    def validate_entity_index(self, session: AgniExtractionSession, entity_index: int) -> None:
        """
        Validate that an entity index is valid for the session.
        
        Args:
            session: AgniExtractionSession instance
            entity_index: Index to validate
            
        Raises:
            ValueError: If index is out of range
        """
        if entity_index < 0 or entity_index >= len(session.entities):
            raise ValueError(f"Invalid entity index: {entity_index}")

    def validate_all_entities_resolved(self, session: AgniExtractionSession) -> None:
        """
        Validate that all entities are in a resolved state.
        
        Args:
            session: AgniExtractionSession instance
            
        Raises:
            ValueError: If any entities are unresolved
        """
        unresolved = []
        for i, entity in enumerate(session.entities):
            if entity.resolution_status not in (
                ResolutionStatus.MATCHED,
                ResolutionStatus.CREATE_NEW,
                ResolutionStatus.SKIPPED
            ):
                unresolved.append(f"Entity {i}: {entity.resolution_status.value}")
        
        if unresolved:
            raise ValueError(f"Unresolved entities: {', '.join(unresolved)}")


def create_agni_service() -> AgniService:
    """
    Factory function to create AgniService with proper dependencies.
    
    Returns:
        Configured AgniService instance
        
    Raises:
        ValueError: If required services cannot be initialized
    """
    
    # Initialize required service dependencies
    search_service = create_search_service()
    genai_service = create_genai_service()
    persistence_service = create_persistence_service()
    
    return AgniService(
        search=search_service,
        genai=genai_service,
        persistence=persistence_service
    )