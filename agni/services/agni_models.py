"""Pydantic models for Agni service."""

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from nes.core.models.entity import Entity, EntityType, EntitySubType


# Full entity type list - type is before slash, subtype is after slash (or None)
ENTITY_TYPES = [
    "person",
    "organization/political_party",
    "organization/government_body",
    "organization/ngo",
    "organization/international_org",
    "organization/media",
    "organization/financial_institution"
]


def parse_entity_type(entity_type_str: str) -> Tuple[str, Optional[str]]:
    """Parse entity type string into (type, subtype) tuple."""
    if "/" in entity_type_str:
        type_part, subtype_part = entity_type_str.split("/", 1)
        return type_part, subtype_part
    return entity_type_str, None


def format_entity_type(entity_type: str, entity_subtype: Optional[str] = None) -> str:
    """Format entity type and subtype into a single string."""
    return f"{entity_type}/{entity_subtype}" if entity_subtype else entity_type


class MessageAuthorType(str, Enum):
    """Message author type."""
    USER = "user"
    AI = "ai"


class Message(BaseModel):
    """A message in a conversation thread."""
    author: MessageAuthorType
    text: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    """Conversation thread for user-AI interactions."""
    thread: List[Message] = Field(default_factory=list)

    def add(self, author: MessageAuthorType, text: str) -> None:
        """Add a message to the thread."""
        self.thread.append(Message(author=author, text=text))


class ConversationKey:
    """Conversation key constants and templates."""
    METADATA_EXTRACTION = "metadata_extraction"
    ENTITY_EXTRACTION = "entity_extraction"

    @staticmethod
    def entity(entity_id: int) -> str:
        """Key for conversation about a specific extracted entity."""
        return f"entity:{entity_id}"


class DocumentMetadata(BaseModel):
    """Extracted document metadata for Nepali governance documents."""
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[date] = None
    document_type: Optional[str] = None
    source: Optional[str] = None

    @classmethod
    def get_genai_extraction_schema(cls) -> dict:
        """Generate JSON schema for GenAI extraction."""
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title in English or Nepali"},
                "summary": {"type": "string", "description": "Brief summary of the document content"},
                "author": {"type": "string", "description": "Document author or publishing entity"},
                "publication_date": {"type": "string", "format": "date", "description": "Publication date (YYYY-MM-DD)"},
                "document_type": {
                    "type": "string",
                    "description": "Type of document",
                    "enum": ["report", "investigation_report", "audit_report", "letter", "official_letter",
                             "complaint_letter", "policy", "law", "regulation", "guideline", "court_case",
                             "court_order", "judgment", "contract", "agreement", "mou", "meeting_minutes",
                             "announcement", "press_release", "budget_document", "financial_statement", "other"]
                },
                "source": {"type": "string", "description": "Document source or originating organization"}
            }
        }


class EntityName(BaseModel):
    """A single name variant for an entity."""
    name: str
    language: str  # 'en' or 'ne'
    is_primary: bool = False


class EntityMatchCandidate(BaseModel):
    """A potential NES match candidate."""
    nes_id: str
    nes_record: Optional[Entity] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None


class ResolvedEntity(BaseModel):
    """Entity reference from initial document extraction."""
    entity_type: str  # Combined type, e.g., "person", "organization/political_party"
    names: List[EntityName] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    mentions: List[str] = Field(default_factory=list)

    @classmethod
    def get_genai_extraction_schema(cls) -> dict:
        """Generate JSON schema for GenAI extraction."""
        return {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "description": "Combined entity type", "enum": ENTITY_TYPES},
                "names": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "language": {"type": "string", "enum": ["en", "ne"]},
                            "is_primary": {"type": "boolean", "default": False}
                        },
                        "required": ["name", "language"]
                    }
                },
                "attributes": {"type": "object", "additionalProperties": True},
                "mentions": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["entity_type", "names"]
        }


class ResolutionStatus(str, Enum):
    """Resolution state for an entity."""
    PENDING = "pending"
    MATCHED = "matched"
    CREATE_NEW = "create_new"
    NEEDS_REVIEW = "needs_review"
    SKIPPED = "skipped"


class EntityMatchState(BaseModel):
    """Entity extracted from document by AI."""
    entity_id: str
    entity_type: Optional[EntityType] = None
    entity_subtype: Optional[EntitySubType] = None
    resolved_entity: Optional[ResolvedEntity] = None
    resolution_status: ResolutionStatus = ResolutionStatus.PENDING
    candidates: List[EntityMatchCandidate] = Field(default_factory=list)
    matched_nes_id: Optional[str] = None
    needs_creation: bool = False
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)


class EntityChange(BaseModel):
    """Entity change to be persisted."""
    entity_type: EntityType
    entity_subtype: Optional[EntitySubType] = None
    entity_data: Dict[str, Any] = Field(default_factory=dict)
    entity_id: Optional[str] = None
    change_type: Literal["create", "update"] = "create"


class AgniExtractionSession(BaseModel):
    """Processing session container."""
    source_document: Optional[Path] = None
    guidance: Optional[str] = None
    metadata: Optional[DocumentMetadata] = None
    conversations: Dict[str, Conversation] = Field(default_factory=dict)
    entities: List[EntityMatchState] = Field(default_factory=list)

    def get_conversation(self, key: str) -> Conversation:
        """Get or create a conversation for the given key."""
        if key not in self.conversations:
            self.conversations[key] = Conversation()
        return self.conversations[key]
