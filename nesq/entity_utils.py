"""
Utility functions for working with NES entities.

TODO: This module contains logic that belongs in the NES package itself.
Once the NES package exposes these utilities, we should remove this file
and import from NES directly to avoid code duplication and ensure we stay
in sync with NES's entity model evolution.
"""

from typing import Any, Dict

from nes.core.models.entity import Entity, EntityType, EntitySubType
from nes.core.models.person import Person
from nes.core.models.organization import (
    Organization,
    PoliticalParty,
    GovernmentBody,
    Hospital,
)
from nes.core.models.location import Location
from nes.core.models.project import Project


def entity_from_dict(data: Dict[str, Any]) -> Entity:
    """Convert a dictionary to an Entity instance.

    Determines the correct entity subclass based on the 'type' and 'sub_type'
    fields in the data, then validates and constructs the appropriate instance.

    This is a local copy of the logic from nes.database.file_database.FileDatabase._entity_from_dict
    to avoid circular dependencies and ensure the validation logic stays in sync with NES.

    TODO: This function should be moved to the NES package as a public utility.
    Once available in NES, import from there instead of maintaining this copy.

    Args:
        data: Dictionary representation of an entity. Must include 'type' field.

    Returns:
        Entity instance of the appropriate subclass (Person, Organization, etc.)

    Raises:
        ValueError: If entity type is invalid or 'type' field is missing
        pydantic.ValidationError: If the data fails validation for the entity type
    """
    if "type" not in data:
        raise ValueError("Entity must have a 'type' field")

    entity_type = EntityType(data["type"])
    entity_subtype = EntitySubType(data["sub_type"]) if data.get("sub_type") else None

    # Determine the correct entity class based on type and subtype
    if entity_type == EntityType.PERSON:
        return Person.model_validate(data)
    elif entity_type == EntityType.ORGANIZATION:
        if entity_subtype == EntitySubType.POLITICAL_PARTY:
            return PoliticalParty.model_validate(data)
        elif entity_subtype == EntitySubType.GOVERNMENT_BODY:
            return GovernmentBody.model_validate(data)
        elif entity_subtype == EntitySubType.HOSPITAL:
            return Hospital.model_validate(data)
        else:
            return Organization.model_validate(data)
    elif entity_type == EntityType.LOCATION:
        return Location.model_validate(data)
    elif entity_type == EntityType.PROJECT:
        return Project.model_validate(data)
    else:
        raise ValueError(f"Unknown entity type: {entity_type}")
