"""
Pytest configuration for test suite.

Ensures environment variables are set to their default values during testing.
"""

import pytest
from django.conf import settings


@pytest.fixture(autouse=True)
def reset_feature_flags(settings):
    """
    Reset all feature flags to their default values for each test.
    
    This ensures tests run with predictable, default behavior unless
    explicitly overridden within a specific test.
    """
    # Reset EXPOSE_CASES_IN_REVIEW to default (False)
    settings.EXPOSE_CASES_IN_REVIEW = False


def create_entities_from_ids(entity_ids):
    """
    Helper function to create JawafEntity objects from entity ID strings.
    
    Args:
        entity_ids: List of entity ID strings (e.g., ['entity:person/test'])
    
    Returns:
        List of JawafEntity objects
    """
    from cases.models import JawafEntity
    
    if not entity_ids:
        return []
    
    entities = []
    for nes_id in entity_ids:
        # Get or create entity with this nes_id
        entity, _ = JawafEntity.objects.get_or_create(nes_id=nes_id)
        entities.append(entity)
    
    return entities


def create_case_with_entities(**kwargs):
    """
    Helper function to create a Case with entity relationships.
    
    Handles conversion of entity ID lists to JawafEntity objects.
    
    Args:
        **kwargs: Case fields, including:
            - alleged_entities: List of entity ID strings
            - related_entities: List of entity ID strings
            - locations: List of entity ID strings
    
    Returns:
        Case object
    """
    from cases.models import Case
    
    # Extract entity fields
    alleged_entity_ids = kwargs.pop('alleged_entities', [])
    related_entity_ids = kwargs.pop('related_entities', [])
    location_ids = kwargs.pop('locations', [])
    
    # Create the case without entities
    case = Case.objects.create(**kwargs)
    
    # Add entities using set()
    if alleged_entity_ids:
        case.alleged_entities.set(create_entities_from_ids(alleged_entity_ids))
    if related_entity_ids:
        case.related_entities.set(create_entities_from_ids(related_entity_ids))
    if location_ids:
        case.locations.set(create_entities_from_ids(location_ids))
    
    return case


def create_document_source_with_entities(**kwargs):
    """
    Helper function to create a DocumentSource with entity relationships.
    
    Handles conversion of entity ID lists to JawafEntity objects.
    
    Args:
        **kwargs: DocumentSource fields, including:
            - related_entity_ids: List of entity ID strings (legacy name)
            - related_entities: List of entity ID strings
    
    Returns:
        DocumentSource object
    """
    from cases.models import DocumentSource
    
    # Extract entity fields (support both old and new names)
    related_entity_ids = kwargs.pop('related_entity_ids', kwargs.pop('related_entities', []))
    
    # Create the source without entities
    source = DocumentSource.objects.create(**kwargs)
    
    # Add entities using set()
    if related_entity_ids:
        source.related_entities.set(create_entities_from_ids(related_entity_ids))
    
    return source
