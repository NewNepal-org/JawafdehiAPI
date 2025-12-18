"""
GenAI service for AI-powered document processing and entity extraction.

Provides functionality for extracting metadata and entities from documents
using AI/ML models, with support for Nepali language content.

This module implements the Extraction class which uses Google Vertex AI
to extract structured data from documents including metadata, entities,
and attributes with confidence scores.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from pathlib import Path
import random
import string
from typing import Any, Dict, List, Optional, Tuple
from dateutil.parser import parse as parse_date

from agni.services.agni_models import (
    AgniExtractionSession,
    DocumentMetadata,
    EntityMatchCandidate,
    EntityMatchState,
    ENTITY_TYPES,
    ResolutionStatus,
    ResolvedEntity,
    parse_entity_type,
    format_entity_type,
    Conversation,
    ConversationKey,
)
from .exceptions import (
    GenAIServiceError,
    LLMAPIError,
    InvalidExtractionError,
    ExtractionTimeoutError,
)
from .prompts import EXTRACTION_SCHEMA, build_system_prompt, build_prompt
from nes.services.scraping.providers.google import GoogleVertexAIProvider

logger = logging.getLogger(__name__)


class GenAIService:
    """
    Service for AI-powered document processing and entity extraction.
    
    This service handles the extraction of metadata, entities, and attributes
    from document content using Google Vertex AI. It assigns confidence scores
    to all extracted fields and stores results in AgniExtractionSession.

    The extraction process:
    1. Builds a prompt with document content, optional guidance, and conversation history
    2. Calls LLM to extract structured data following the extraction schema
    3. Parses and validates the raw extraction result
    4. Creates DocumentMetadata and ExtractedEntity objects
    5. Stores the result in AgniExtractionSession
    """
    
    def __init__(self, llm_provider: Any, max_retries: int = 3, timeout: int = 60):
        """Initialize GenAI service.
        
        Args:
            llm_provider: GoogleVertexAIProvider instance
            max_retries: Maximum number of retry attempts for LLM calls (default: 3)
            timeout: Timeout in seconds for LLM calls (default: 60)

        Raises:
            ValueError: If max_retries or timeout are invalid
        """
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")

        if timeout <= 0:
            raise ValueError(f"timeout must be > 0, got {timeout}")

        self.llm_provider = llm_provider
        self.max_retries = max_retries
        self.timeout = timeout
        logger.info("GenAI service initialized")
    
    async def extract_metadata(
        self, 
        document: Path, 
        session: AgniExtractionSession
    ) -> DocumentMetadata:
        """
        Extract document metadata using AI.
        
        Args:
            document: Path to the document file
            session: AgniExtractionSession for context and storing results
            
        Returns:
            DocumentMetadata instance with extracted information
            
        Raises:
            GenAIServiceError: If metadata extraction fails
        """
        logger.info(f"Starting metadata extraction for document {document}")

        try:
            # Read document content
            content = document.read_text(encoding='utf-8')
            
            # Get conversation for context
            conversation = session.get_conversation(ConversationKey.METADATA_EXTRACTION)
            
            # Extract with AI
            raw_extraction = await self._extract_with_ai(
                content=content,
                guidance=session.guidance,
                conversation=conversation,
                extraction_type="metadata"
            )

            # Parse metadata
            metadata = self._parse_metadata(raw_extraction["metadata"])
            raw_entities = raw_extraction.get("entities", [])
            resolved_entities = [ResolvedEntity(**entity) for entity in raw_entities]
            entities = self._parse_entities(resolved_entities)
            
            # Store in session
            session.metadata = metadata
            session.entities = entities
            session.source_document = document

            logger.info(f"Metadata extraction complete for document {document}")
            return metadata, entities

        except Exception as e:
            logger.error(f"Metadata extraction failed for document {document}: {e}", exc_info=True)
            raise GenAIServiceError(f"Metadata extraction failed: {e}") from e
    
    async def extract_entities(
        self, 
        document: Path, 
        session: AgniExtractionSession
    ) -> List[EntityMatchState]:
        """
        Extract entities from document using AI.
        
        Args:
            document: Path to the document file
            session: AgniExtractionSession containing metadata and storing results
            
        Returns:
            List of ExtractedEntity instances
            
        Raises:
            GenAIServiceError: If entity extraction fails
        """
        logger.info(f"Starting entity extraction for document {document}")

        try:
            if not session.metadata:
                raise GenAIServiceError("Metadata must be extracted before entities")

            # Read document content
            content = document.read_text(encoding='utf-8')
            
            # Get conversation for context
            conversation = session.get_conversation(ConversationKey.ENTITY_EXTRACTION)
            
            # Extract with AI
            raw_extraction = await self._extract_with_ai(
                content=content,
                guidance=session.guidance,
                conversation=conversation,
                extraction_type="entities",
                metadata_context=session.metadata
            )

            # Parse entities
            entities = self._parse_entities(raw_extraction["entities"])
            
            # Store in session
            session.entities = entities

            logger.info(f"Entity extraction complete for document {document}: {len(entities)} entities extracted")
            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed for document {document}: {e}", exc_info=True)
            raise GenAIServiceError(f"Entity extraction failed: {e}") from e
    
    async def resolve_entity_candidates(
        self,
        entity: EntityMatchState,
        metadata: Optional[DocumentMetadata],
    ) -> Tuple[List["EntityMatchCandidate"], Dict[str, Any]]:
        """
        Resolve entity candidates and generate proposed changes using AI.
        
        For entities with candidates: evaluates confidence scores and generates diffs.
        For entities without candidates: generates complete new entity data.
        
        Args:
            entity: EntityMatchState with candidates already populated from search
            metadata: Document metadata for context
            
        Returns:
            Tuple of (scored_candidates, proposed_changes)
            
        Raises:
            GenAIServiceError: If resolution fails
        """
        from agni.services.agni_models import EntityMatchCandidate
        
        if entity.candidates:
            logger.info(f"Evaluating {len(entity.candidates)} candidates for entity {entity.entity_id}")
            return await self._evaluate_existing_candidates(entity, metadata)
        else:
            logger.info(f"Generating new entity data for {entity.entity_id}")
            proposed_changes = await self._generate_new_entity_data(entity, metadata)
            return [], proposed_changes

    async def _evaluate_existing_candidates(
        self,
        entity: EntityMatchState,
        metadata: Optional[DocumentMetadata],
    ) -> Tuple[List["EntityMatchCandidate"], Dict[str, Any]]:
        """Evaluate existing NES candidates and generate proposed changes."""
        try:
            # Build context for AI
            candidates_context = self._build_candidates_context(entity.candidates)
            entity_context = self._build_entity_context(entity)
            metadata_context = metadata.model_dump() if metadata else {}
            
            # Get entity-type-specific schema
            proposed_changes_schema = self._get_entity_schema(
                entity.entity_type, entity.entity_subtype
            )
            
            system_prompt = self._build_evaluate_candidates_system_prompt(
                entity.entity_type, entity.entity_subtype
            )
            user_prompt = self._build_evaluate_candidates_prompt(
                entity_context=entity_context,
                candidates_context=candidates_context,
                metadata_context=metadata_context,
            )
            
            response_schema = {
                "type": "object",
                "properties": {
                    "candidates": {
                        "type": "array",
                        "description": "Confidence scores for each candidate",
                        "items": {
                            "type": "object",
                            "properties": {
                                "nes_id": {"type": "string"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "reasoning": {"type": "string"},
                            },
                            "required": ["nes_id", "confidence"],
                        },
                    },
                    "proposed_changes": proposed_changes_schema,
                },
                "required": ["candidates", "proposed_changes"],
            }
            
            result = await asyncio.wait_for(
                self.llm_provider.extract_structured_data(
                    text=user_prompt,
                    schema=response_schema,
                    instructions=system_prompt,
                ),
                timeout=self.timeout,
            )
            
            # Update candidate confidence scores
            confidence_map = {c["nes_id"]: c for c in result.get("candidates", [])}
            for candidate in entity.candidates:
                if candidate.nes_id in confidence_map:
                    candidate.confidence = confidence_map[candidate.nes_id].get(
                        "confidence", candidate.confidence
                    )
            
            # Sort by confidence descending
            entity.candidates.sort(key=lambda c: c.confidence or 0, reverse=True)
            
            proposed_changes = result.get("proposed_changes", {})
            
            logger.info(f"Candidate evaluation complete for entity {entity.entity_id}")
            return entity.candidates, proposed_changes
            
        except asyncio.TimeoutError as e:
            logger.error(f"Candidate evaluation timed out: {e}")
            raise ExtractionTimeoutError(f"Candidate evaluation timed out") from e
        except Exception as e:
            logger.error(f"Candidate evaluation failed: {e}", exc_info=True)
            raise GenAIServiceError(f"Candidate evaluation failed: {e}") from e

    async def _generate_new_entity_data(
        self,
        entity: EntityMatchState,
        metadata: Optional[DocumentMetadata],
    ) -> Dict[str, Any]:
        """Generate proposed data for creating a new NES entity."""
        try:
            entity_context = self._build_entity_context(entity)
            metadata_context = metadata.model_dump() if metadata else {}
            
            # Get entity-type-specific schema
            entity_schema = self._get_entity_schema(
                entity.entity_type, entity.entity_subtype
            )
            
            system_prompt = self._build_new_entity_system_prompt(
                entity.entity_type, entity.entity_subtype
            )
            user_prompt = self._build_new_entity_prompt(
                entity_context=entity_context,
                metadata_context=metadata_context,
            )
            
            result = await asyncio.wait_for(
                self.llm_provider.extract_structured_data(
                    text=user_prompt,
                    schema=entity_schema,
                    instructions=system_prompt,
                ),
                timeout=self.timeout,
            )
            
            logger.info(f"New entity data generation complete for {entity.entity_id}")
            return result
            
        except asyncio.TimeoutError as e:
            logger.error(f"New entity generation timed out: {e}")
            raise ExtractionTimeoutError(f"New entity generation timed out") from e
        except Exception as e:
            logger.error(f"New entity generation failed: {e}", exc_info=True)
            raise GenAIServiceError(f"New entity generation failed: {e}") from e

    def _build_candidates_context(
        self, candidates: List[EntityMatchCandidate]
    ) -> List[Dict[str, Any]]:
        """Build context dict for candidates."""
        result = []
        for candidate in candidates:
            if not candidate.nes_record:
                raise ValueError("Candidate has no NES Record")
            info = {
                "nes_id": candidate.nes_id,
                "initial_confidence": candidate.confidence,
                "candidate_details": candidate.nes_record.model_dump()
            }
            result.append(info)
        return result

    def _build_entity_context(self, entity: EntityMatchState) -> Dict[str, Any]:
        """Build context dict for extracted entity."""
        return {
            "entity_type": format_entity_type(entity.entity_type, entity.entity_subtype),
            "resolved_entity": (
                entity.resolved_entity.model_dump() if entity.resolved_entity else None
            ),
        }

    def _get_entity_schema(
        self, entity_type: str, entity_subtype: Optional[str]
    ) -> Dict[str, Any]:
        """
        Get JSON schema for proposed_changes based on entity type/subtype.
        
        Returns a schema matching the NES entity model structure.
        """
        # Common name schema
        name_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "language": {"type": "string", "enum": ["en", "ne"]},
                "kind": {"type": "string", "enum": ["primary", "alias", "former"]},
            },
            "required": ["name", "language"],
        }
        
        lang_text_schema = {
            "type": "object",
            "properties": {
                "en": {"type": "string"},
                "ne": {"type": "string"},
            },
        }
        
        # Base schema common to all entities
        base_schema = {
            "type": "object",
            "properties": {
                "names": {
                    "type": "array",
                    "items": name_schema,
                    "description": "Entity names in English and Nepali",
                },
                "short_description": lang_text_schema,
                "description": lang_text_schema,
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        }
        
        if entity_type == "person":
            base_schema["properties"]["personal_details"] = {
                "type": "object",
                "properties": {
                    "birth_date": {"type": "string", "description": "YYYY, YYYY-MM, or YYYY-MM-DD"},
                    "gender": {"type": "string", "enum": ["male", "female", "other"]},
                    "birth_place": {
                        "type": "object",
                        "properties": {
                            "district": {"type": "string"},
                            "province": {"type": "string"},
                        },
                    },
                    "father_name": lang_text_schema,
                    "mother_name": lang_text_schema,
                    "spouse_name": lang_text_schema,
                    "positions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": lang_text_schema,
                                "organization": lang_text_schema,
                                "start_date": {"type": "string", "format": "date"},
                                "end_date": {"type": "string", "format": "date"},
                            },
                        },
                    },
                },
            }
            
        elif entity_type == "organization":
            if entity_subtype == "political_party":
                base_schema["properties"]["address"] = {
                    "type": "object",
                    "properties": {
                        "district": {"type": "string"},
                        "province": {"type": "string"},
                    },
                }
                base_schema["properties"]["party_chief"] = lang_text_schema
                base_schema["properties"]["registration_date"] = {
                    "type": "string", "format": "date"
                }
                base_schema["properties"]["symbol"] = {
                    "type": "object",
                    "properties": {"name": lang_text_schema},
                }
            elif entity_subtype == "government_body":
                base_schema["properties"]["government_type"] = {
                    "type": "string",
                    "enum": ["federal", "provincial", "local", "other", "unknown"],
                }
            elif entity_subtype == "hospital":
                base_schema["properties"]["beds"] = {"type": "integer"}
                base_schema["properties"]["services"] = {
                    "type": "array", "items": {"type": "string"}
                }
                base_schema["properties"]["ownership"] = {
                    "type": "string", "enum": ["Private", "Public", "Government"]
                }
                base_schema["properties"]["address"] = {
                    "type": "object",
                    "properties": {
                        "district": {"type": "string"},
                        "province": {"type": "string"},
                    },
                }
                
        elif entity_type == "location":
            base_schema["properties"]["parent"] = {
                "type": "string", "description": "Entity ID of parent location"
            }
            base_schema["properties"]["area"] = {
                "type": "number", "description": "Area in square kilometers"
            }
            base_schema["properties"]["lat"] = {"type": "number"}
            base_schema["properties"]["lng"] = {"type": "number"}
        
        return base_schema

    def _build_evaluate_candidates_system_prompt(
        self, entity_type: str, entity_subtype: Optional[str]
    ) -> str:
        """Build system prompt for candidate evaluation."""
        type_desc = f"{entity_subtype} {entity_type}" if entity_subtype else entity_type
        return f"""You are an expert at matching extracted entities to existing database records for Nepali governance data.

Your task is to:
1. Evaluate how well each candidate NES record matches the extracted {type_desc} entity
2. Assign a confidence score (0.0 to 1.0) based on name similarity, type match, and contextual relevance
3. Generate proposed_changes - a diff of fields to update on the best matching record

Confidence scoring guidelines:
- 0.95-1.0: Near-perfect match (same name, type, and attributes align)
- 0.8-0.94: Strong match (names match well, types align, minor differences)
- 0.6-0.79: Moderate match (similar names, compatible types, some uncertainty)
- 0.4-0.59: Weak match (partial name match, possible type mismatch)
- Below 0.4: Poor match (unlikely to be the same entity)

For proposed_changes:
- Include only fields that should be updated or added based on the document
- Use both English and Nepali names where available
- Preserve existing data that isn't contradicted by the document"""

    def _build_evaluate_candidates_prompt(
        self,
        entity_context: Dict[str, Any],
        candidates_context: List[Dict[str, Any]],
        metadata_context: Dict[str, Any],
    ) -> str:
        """Build user prompt for candidate evaluation."""
        return f"""Evaluate the following entity match candidates.

## Document Context
{json.dumps(metadata_context, indent=2, ensure_ascii=False, default=str)}

## Extracted Entity
{json.dumps(entity_context, indent=2, ensure_ascii=False, default=str)}

## Candidate NES Records
{json.dumps(candidates_context, indent=2, ensure_ascii=False, default=str)}

Provide confidence scores for each candidate and proposed_changes for the best match."""

    def _build_new_entity_system_prompt(
        self, entity_type: str, entity_subtype: Optional[str]
    ) -> str:
        """Build system prompt for new entity generation."""
        type_desc = f"{entity_subtype} {entity_type}" if entity_subtype else entity_type
        return f"""You are an expert at structuring entity data for the Nepal Entity Service (NES).

Your task is to generate complete entity data for a new {type_desc} entity based on information extracted from a document.

Guidelines:
- Include names in both English and Nepali where available
- Mark the most commonly used name as primary (kind: "primary")
- Include all relevant attributes based on the entity type
- Use accurate Nepali administrative divisions (province, district, municipality)
- Leave fields empty/null if information is not available in the document"""

    def _build_new_entity_prompt(
        self,
        entity_context: Dict[str, Any],
        metadata_context: Dict[str, Any],
    ) -> str:
        """Build user prompt for new entity generation."""
        return f"""Generate complete entity data for a new NES record.

## Document Context
{json.dumps(metadata_context, indent=2, ensure_ascii=False, default=str)}

## Extracted Entity Information
{json.dumps(entity_context, indent=2, ensure_ascii=False, default=str)}

Generate the entity data following the schema."""

    async def update_entity(
        self, 
        entity: EntityMatchState, 
        session: AgniExtractionSession,
        conversation: Conversation
    ) -> EntityMatchState:
        """
        Update entity based on conversation history using AI.
        
        Args:
            entity: ExtractedEntity instance to update
            session: AgniExtractionSession with document context
            conversation: Conversation with user messages and AI responses
            
        Returns:
            Updated ExtractedEntity instance
            
        Raises:
            GenAIServiceError: If entity update fails
        """
        logger.info(f"Starting entity update for {entity.entity_type}")

        try:
            # Get document content for context
            if not session.document:
                raise GenAIServiceError("No document available for entity update")
                
            content = session.document.read_text(encoding='utf-8')
            
            # Extract with AI for update
            raw_extraction = await self._extract_with_ai(
                content=content,
                guidance=session.guidance,
                conversation=conversation,
                extraction_type="entity_update",
                entity_context=entity
            )

            # Parse updated entity
            updated_entities = self._parse_entities(raw_extraction["entities"])
            if not updated_entities:
                raise InvalidExtractionError("No updated entity returned from AI")
                
            updated_entity = updated_entities[0]
            
            logger.info(f"Entity update complete for {entity.entity_type}")
            return updated_entity

        except Exception as e:
            logger.error(f"Entity update failed: {e}", exc_info=True)
            raise GenAIServiceError(f"Entity update failed: {e}") from e

    async def _extract_with_ai(
        self,
        content: str,
        guidance: Optional[str] = None,
        conversation: Optional[Conversation] = None,
        extraction_type: str = "full",
        metadata_context: Optional[DocumentMetadata] = None,
        entity_context: Optional[EntityMatchState] = None,
    ) -> Dict[str, Any]:
        """Call LLM to extract structured data from content with retry logic.

        Args:
            content: Document text content to extract from
            guidance: Optional guidance for context-specific extraction
            conversation: Optional conversation history for context
            extraction_type: Type of extraction ("metadata", "entities", "full", "entity_update")
            metadata_context: Optional metadata for context
            entity_context: Optional entity for updates

        Returns:
            Dict with extraction data

        Raises:
            LLMAPIError: If LLM API fails after all retries
            InvalidExtractionError: If LLM returns invalid response
            ExtractionTimeoutError: If LLM call times out
        """
        logger.debug(f"Building extraction prompt for type: {extraction_type}")

        # Build system prompt with task-specific context
        system_prompt = build_system_prompt(
            extraction_type=extraction_type,
            guidance=guidance,
            metadata_context=metadata_context,
            entity_context=entity_context,
        )

        # Build user prompt with content and conversation history
        prompt = build_prompt(
            content=content,
            guidance=guidance,
            conversation=conversation,
            extraction_type=extraction_type,
            metadata_context=metadata_context,
            entity_context=entity_context,
        )

        # Retry with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Calling LLM provider for extraction (attempt {attempt + 1}/{self.max_retries + 1})")

                # Call LLM provider with timeout
                result = await asyncio.wait_for(
                    self.llm_provider.extract_structured_data(
                        text=prompt,
                        schema=EXTRACTION_SCHEMA,
                        instructions=system_prompt,
                    ),
                    timeout=self.timeout,
                )

                # Validate response structure
                if not isinstance(result, dict):
                    raise InvalidExtractionError(f"LLM returned invalid response type: {type(result)}")

                logger.debug("LLM extraction successful")
                return result

            except asyncio.TimeoutError as e:
                logger.error(f"LLM extraction timed out after {self.timeout}s: {e}")
                raise ExtractionTimeoutError(f"LLM extraction timed out after {self.timeout} seconds") from e

            except InvalidExtractionError:
                # Don't retry for invalid responses
                raise

            except Exception as e:
                last_exception = e
                logger.warning(f"LLM extraction attempt {attempt + 1} failed: {e}", exc_info=True)

                # Don't sleep after last attempt
                if attempt < self.max_retries:
                    # Exponential backoff: 1s, 2s, 4s, ...
                    backoff_time = 2**attempt
                    logger.info(f"Retrying in {backoff_time}s...")
                    await asyncio.sleep(backoff_time)

        # All retries exhausted
        error_msg = f"LLM extraction failed after {self.max_retries + 1} attempts"
        if last_exception:
            error_msg += f": {last_exception}"
        logger.error(error_msg)
        raise LLMAPIError(error_msg) from last_exception

    def _parse_metadata(self, raw_metadata: Dict[str, Any]) -> DocumentMetadata:
        """Parse raw metadata dict into DocumentMetadata object.

        Args:
            raw_metadata: Raw metadata dict from LLM

        Returns:
            DocumentMetadata object with parsed fields
        """
        return DocumentMetadata(
            title=raw_metadata.get("title"),
            summary=raw_metadata.get("summary"),
            author=raw_metadata.get("author"),
            publication_date=parse_date(raw_metadata.get("publication_date")).date() if raw_metadata.get("publication_date") else None,
            document_type=raw_metadata.get("document_type"),
            source=raw_metadata.get("source"),
        )

    def _parse_entities(self, resolved_entities: List[ResolvedEntity]) -> List[EntityMatchState]:
        """Parse raw entities list into ExtractedEntity objects.

        Args:
            resolved_entities: List of raw entity dicts from LLM

        Returns:
            List of ExtractedEntity objects
        """
        entities = []

        for resolved_entity in resolved_entities:
            # Get entity type from new format
            entity_type_full = resolved_entity.entity_type
            if not entity_type_full:
                raise ValueError("Entity must have 'entity_type' field")

            # Validate entity type
            if entity_type_full not in ENTITY_TYPES:
                raise ValueError(f"Invalid entity type: {entity_type_full}")

            entity_type, entity_subtype = parse_entity_type(entity_type_full)

            # Generate a random entity ID of 8 characters
            entity_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

            # Create ExtractedEntity
            entity = EntityMatchState(
                entity_id=entity_id,
                entity_type=entity_type,
                entity_subtype=entity_subtype,
                resolution_status=ResolutionStatus.PENDING,
                resolved_entity=resolved_entity
            )

            entities.append(entity)

        return entities

    def _get_user_messages(self, conversation: Conversation) -> List[str]:
        """Extract user messages from conversation.

        Args:
            conversation: Conversation object

        Returns:
            List of user message texts
        """
        return [msg.text for msg in conversation.thread if msg.author.value == "user"]


def create_genai_service(model_id: str = "gemini-2.5-flash") -> GenAIService:
    """
    Factory function to create GenAI service with GoogleVertexAIProvider.

    Args:
        model_id: Vertex AI model ID to use (default: "gemini-2.5-flash")
        
    Returns:
        Configured GenAI service instance
        
    Raises:
        ImportError: If GoogleVertexAIProvider is not available
        GenAIServiceError: If service initialization fails or credentials are invalid
        
    Example:
        >>> # Set environment variable
        >>> os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/service-account.json'
        >>> # Create service
        >>> genai_service = create_genai_service()
        >>> # Use with AgniService
        >>> agni_service = create_agni_service()
    """
    try:        
        # Get project_id from GOOGLE_APPLICATION_CREDENTIALS
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        project_id = None

        if credentials_path is None:
            raise GenAIServiceError("GOOGLE_APPLICATION_CREDENTIALS not set!")

        with open(credentials_path) as f:
            credentials_data = json.load(f)
            project_id = credentials_data.get('project_id')
            logger.info(f"Extracted project_id from credentials: {project_id}")
        
        if not project_id:
            raise GenAIServiceError(
                "Could not determine project_id from GOOGLE_APPLICATION_CREDENTIALS. "
                "Ensure the credentials file contains a valid 'project_id' field."
            )
        
        # Initialize GoogleVertexAIProvider with project_id
        llm_provider = GoogleVertexAIProvider(
            project_id=project_id,
            model_id=model_id,
        )
        
        return GenAIService(llm_provider)
        
    except ImportError as e:
        logger.error(f"Failed to import GoogleVertexAIProvider: {e}")
        raise GenAIServiceError(f"GoogleVertexAIProvider not available: {e}") from e
    except Exception as e:
        logger.error(f"Failed to create GenAI service: {e}")
        raise GenAIServiceError(f"Service initialization failed: {e}") from e