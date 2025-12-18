"""
Search service for entity matching and resolution.

Provides functionality to search for existing entities in the NES database
and find potential matches for extracted entities from documents.
"""

from copy import copy
import logging
from typing import List, Optional, Dict, Any
from django.conf import settings
import requests
from nes.core.utils.entity_converter import entity_from_dict
from .agni_models import EntityMatchState, EntityMatchCandidate

logger = logging.getLogger(__name__)


class SearchServiceError(Exception):
    """Exception raised when search operations fail."""
    pass


class SearchService:
    """
    Service for searching and matching entities against the NES database.
    
    This service handles entity resolution by finding potential matches
    for extracted entities and providing confidence scores.
    """
    
    def __init__(self, nes_base_url: str, timeout: int = 30):
        """
        Initialize SearchService with NES API configuration.
        
        Args:
            nes_base_url: Base URL of the NES API
            timeout: Request timeout in seconds
        """
        self.nes_base_url = nes_base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        # Set a user agent to identify our client
        self.session.headers.update({
            'User-Agent': 'JawafdehiAPI-SearchService/1.0'
        })
    
    def find_matches(self, entity: EntityMatchState) -> List[Any]:
        """
        Find potential matches for an extracted entity.
        
        Args:
            entity: ExtractedEntity instance to find matches for
            
        Returns:
            List of MatchEntityCandidate objects sorted by confidence
            
        Raises:
            SearchServiceError: If the search fails
        """
        try:
            # Prepare search parameters
            search_params = self._prepare_search_params(entity)
            
            # Search for matches in NES
            candidates = self._search_nes_entities(search_params)

            logger.info(f"Found {len(candidates)} candidates for entity {entity.resolved_entity.names[0].name}")
            return candidates
            
        except Exception as e:
            logger.error(f"Error finding matches for entity: {e}")
            raise SearchServiceError(f"Entity search failed: {str(e)}")
    
    def _prepare_search_params(self, entity: EntityMatchState) -> Dict[str, Any]:
        """
        Prepare search parameters from extracted entity.
        
        Args:
            entity: ExtractedEntity instance
            
        Returns:
            Dictionary of search parameters for NES API
        """
        name = entity.resolved_entity.names[0].name
        params = {
            'entity_type': entity.entity_type,
            'query': name,
            'limit': 5  # Maximum number of candidates to return
        }
        
        # Add entity sub-type if available
        if entity.entity_subtype:
            params['sub_type'] = entity.entity_subtype
        
        return params
    
    
    def _search_nes_entities(self, search_params: Dict[str, Any]) -> List[EntityMatchCandidate]:
        """
        Search for entities in the NES database.
        
        Args:
            search_params: Search parameters for the NES API
            
        Returns:
            List of matching entities with confidence scores
            
        Raises:
            SearchServiceError: If the NES API request fails
        """
        try:
            search_params = copy(search_params)
            search_params.setdefault("limit", 10)
            search_params.setdefault("offset", 0)
            
            # Make GET request to NES entities API (following the working example)
            response = self.session.get(
                f"{self.nes_base_url}/entities",
                params=search_params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            search_results = response.json()
            
            # Process results without confidence calculation
            matches = []
            for result in search_results.get('entities', []):
                del result["id"]
                del result["version_summary"]["id"]

                nes_record = entity_from_dict(result)
                
                match = EntityMatchCandidate(
                    nes_id=nes_record.id,
                    nes_record=nes_record,
                    confidence=None,
                )

                matches.append(match)
            
            return matches
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NES API request failed: {e}")
            raise SearchServiceError(f"NES search request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing NES search results: {e}")
            raise SearchServiceError(f"Search result processing failed: {str(e)}")


def create_search_service() -> SearchService:
    """
    Factory function to create SearchService with proper configuration.
    
    Returns:
        Configured SearchService instance
        
    Raises:
        ValueError: If required configuration is missing
    """
    nes_base_url = getattr(settings, 'NES_API_URL', "https://nes.newnepal.org")

    if not nes_base_url:
        raise ValueError("NES_API_URL setting is required for SearchService")
    
    timeout = getattr(settings, 'NES_REQUEST_TIMEOUT', 30)
    
    return SearchService(
        nes_base_url=nes_base_url,
        timeout=timeout
    )