"""Pydantic payload validators for the NES Queue System (NESQ).

Provides action-specific payload validation using Pydantic v2 models.
Each queue action (e.g., ADD_NAME) has a corresponding Pydantic model that
validates the payload structure before a NESQueueItem is created.

MVP: Only AddNamePayload is supported. CREATE_ENTITY and UPDATE_ENTITY
will be added in future releases.

See .kiro/specs/nes-queue-system/ for full specification.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field, field_validator

from nes.core.identifiers.validators import validate_entity_id
from nes.core.models.base import Name

from nesq.entity_utils import entity_from_dict


class AddNamePayload(BaseModel):
    """Payload for ADD_NAME action — adds a name or misspelling to an existing entity.

    MVP: This is the only supported action in the initial release.
    Future: CREATE_ENTITY and UPDATE_ENTITY will be added later.

    Uses the NES ``Name`` model directly for name validation, ensuring
    consistency with the NES data schema (NameKind enum, NameParts structure,
    and at-least-one-language constraint).

    Example payload::

        {
            "entity_id": "entity:person/sher-bahadur-deuba",
            "name": {
                "kind": "ALIAS",
                "en": {"full": "S.B. Deuba"}
            },
            "is_misspelling": false
        }
    """

    entity_id: str = Field(
        ...,
        description="NES entity ID to add the name to (e.g. 'entity:person/sher-bahadur-deuba').",
    )
    name: Name = Field(
        ...,
        description="Name object validated by the NES Name model (kind + at least one language).",
    )
    is_misspelling: bool = Field(
        default=False,
        description=(
            "If True, the name is added to the entity's misspelled_names list. "
            "If False (default), it is added to the regular names list."
        ),
    )

    @field_validator("entity_id")
    @classmethod
    def validate_entity_id_format(cls, v: str) -> str:
        """Validate entity_id using the NES validator.

        Delegates to ``nes.core.identifiers.validators.validate_entity_id``
        which checks type, subtype, and slug format/length constraints.

        Raises:
            ValueError: If the entity ID format is invalid.
        """
        validate_entity_id(v)
        return v


class CreateEntityPayload(BaseModel):
    """Payload for CREATE_ENTITY action — creates a new entity in the NES database.

    The entity_data field is validated by delegating to the appropriate NES
    entity model (Person, Organization, Location, Project) based on entity_type
    and entity_subtype. This ensures that as the entity schema evolves, the
    validation stays in sync with the NES models.

    Example payload::

        {
            "entity_data": {
                "type": "person",
                "sub_type": null,
                "slug": "sher-bahadur-deuba",
                "names": [
                    {
                        "kind": "PRIMARY",
                        "en": {"full": "Sher Bahadur Deuba"},
                        "ne": {"full": "शेर बहादुर देउबा"}
                    }
                ],
                "tags": ["politician", "prime-minister"],
                "personal_details": {
                    "gender": "male"
                },
                "version_summary": {...},
                "created_at": "2024-01-01T00:00:00Z"
            },
            "author_id": "jawafdehi:contributor_user"
        }

    Note: The entity_data must include 'type' field. The 'version_summary'
    and 'created_at' fields will be added by the processor if not present.
    """

    entity_data: Dict[str, Any] = Field(
        ...,
        description=(
            "Complete entity data dictionary. Must include 'type' field. "
            "Will be validated against the appropriate NES entity model "
            "(Person, Organization, Location, Project)."
        ),
    )
    author_id: str = Field(
        ...,
        description="Author ID in the format 'jawafdehi:username'.",
    )

    @field_validator("entity_data")
    @classmethod
    def validate_entity_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate entity_data using the appropriate NES entity model.

        This delegates to entity_from_dict which will:
        1. Check that 'type' field is present
        2. Determine the correct entity class (Person, Organization, etc.)
        3. Validate all fields against that entity's Pydantic model

        Note: We allow missing version_summary and created_at since those
        will be added by the processor.
        """
        if "type" not in v:
            raise ValueError("entity_data must include 'type' field")

        # Create a copy with dummy version_summary and created_at if missing
        # (these will be added by the processor)
        validation_data = v.copy()
        if "version_summary" not in validation_data:
            validation_data["version_summary"] = {
                "entity_or_relationship_id": "dummy",
                "type": "ENTITY",
                "version_number": 1,
                "author": {"slug": "dummy"},
                "change_description": "dummy",
                "created_at": "2024-01-01T00:00:00Z",
            }
        if "created_at" not in validation_data:
            validation_data["created_at"] = "2024-01-01T00:00:00Z"

        # Validate using the appropriate NES entity model
        try:
            entity_from_dict(validation_data)
        except Exception as e:
            raise ValueError(f"Invalid entity_data: {str(e)}")

        return v


def validate_action_payload(action: str, payload: Dict[str, Any]) -> BaseModel:
    """Validate a payload using the Pydantic model for the given action.

    MVP: Only ADD_NAME is supported in this version.

    Args:
        action: The QueueAction value (e.g. "ADD_NAME", "CREATE_ENTITY").
        payload: The raw payload dictionary to validate.

    Returns:
        A validated Pydantic model instance.

    Raises:
        ValueError: If the action is not supported.
        pydantic.ValidationError: If the payload fails validation.
    """
    if action == "ADD_NAME":
        return AddNamePayload(**payload)
    elif action == "CREATE_ENTITY":
        return CreateEntityPayload(**payload)

    raise ValueError(
        f"Action '{action}' is not supported in this version. "
        "Only ADD_NAME and CREATE_ENTITY are available."
    )
