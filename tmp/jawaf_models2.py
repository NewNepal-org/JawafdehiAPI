from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AllegationType(str, Enum):
    """Types of allegations."""

    CORRUPTION = "corruption"
    MISCONDUCT = "misconduct"
    BREACH_OF_TRUST = "breach_of_trust"
    BROKEN_PROMISE = "broken_promise"
    MEDIA_TRIAL = "media_trial"


class AllegationStatus(str, Enum):
    """Status of an allegation via official channels."""

    UNDER_INVESTIGATION = "under_investigation"
    CLOSED = "closed"


class AllegationLifecycleState(str, Enum):
    """Allegation internal lifecycle."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    CURRENT = "current"
    CLOSED = "closed"


class ModificationAction(str, Enum):
    """Types of modifications to an allegation."""

    CREATED = "created"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    UPDATED = "updated"
    RESPONSE_ADDED = "response_added"


class ModificationEntry(BaseModel):
    """Single entry in modification trail."""

    model_config = ConfigDict(extra="forbid")

    action: ModificationAction = Field(..., description="Type of modification")
    timestamp: datetime = Field(..., description="When modification occurred")
    actor: Optional[str] = Field(None, description="Who made the modification")
    notes: Optional[str] = Field(None, description="Additional notes")


class EvidenceSourceType(str, Enum):
    """Source of evidence."""

    GOVERNMENT = "government"
    NGO = "ngo"
    SOCIAL_MEDIA = "social_media"
    CROWDSOURCED = "crowdsourced"
    OTHER = "other"


class Evidence(BaseModel):
    """Evidence supporting an allegation."""

    evidence_id: str = Field(..., description="Unique ID of the evidence")
    description: str = Field(..., description="Description of the evidence")
    url: Optional[str] = Field(None, description="URL to evidence source")
    source_type: EvidenceSourceType = Field(..., description="Type of evidence source")


class TimelineEvent(BaseModel):
    """Single event in allegation timeline."""

    date: datetime = Field(..., description="When event occurred")
    title: str = Field(..., max_length=200, description="Event title")
    description: str = Field(..., description="Event description")
    evidence_ids: List[str] = Field(..., description="Evidences supporting the event")
    source_url: Optional[str] = Field(None, description="URL to source")


class Response(BaseModel):
    """Response from alleged entity."""

    response_text: str = Field(..., description="Response from the alleged entity")
    entity_id: str = Field(..., description="Entity ID of the responding entity")
    evidence_ids: List[str] = Field(
        ..., description="Evidences supporting the response"
    )
    submitted_at: datetime = Field(..., description="When response was submitted")
    verified_at: Optional[datetime] = Field(
        None, description="When response was verified"
    )
    verified_by: Optional[str] = Field(None, description="Who verified the response")


class Allegation(BaseModel):
    allegation_type: AllegationType = Field(..., description="Type of allegation")
    state: AllegationLifecycleState = Field(..., description="Current lifecycle state")

    title: str = Field(..., max_length=200, description="Brief allegation title")
    alleged_entities: List[str] = Field(
        ..., description="Entities involved in the allegation"
    )
    related_entities: List[str] = Field(..., description="Other related entities")

    location_id: Optional[str] = Field(None, description="Location of the allegation")

    description: str = Field(..., description="Full markdown content (multi-page)")
    key_allegatioons: str = Field(..., description="Key allegations")

    status: Optional[AllegationStatus] = Field(
        None, description="Current status of the allegation"
    )

    evidences: List[Evidence] = Field(
        default_factory=list, description="Supporting evidences"
    )

    status: AllegationStatus = Field(
        default=AllegationStatus.SUBMITTED, description="Current status"
    )

    timeline: List[TimelineEvent] = Field(
        default_factory=list, description="Chronological timeline of events"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Allegation "
    )

    first_public_date: datetime = Field(
        default_factory=datetime.now, description="First public date"
    )

    responses: List[Response] = Field(
        default_factory=list, description="Responses from alleged entity"
    )

    modification_trail: List[ModificationEntry] = Field(
        default_factory=list, description="Complete audit trail of all modifications"
    )
