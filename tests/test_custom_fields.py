"""
Property-based tests for custom list field validation.

Feature: accountability-platform-core
Property 2: Draft validation is lenient, In Review validation is strict
Validates: Requirements 1.2
"""

import pytest
from hypothesis import given, strategies as st, settings
from django.core.exceptions import ValidationError
from cases.fields import (
    TextListField,
    TimelineListField,
    EvidenceListField,
)


# ============================================================================
# Hypothesis Strategies (Generators)
# ============================================================================

@st.composite
def valid_entity_id(draw):
    """Generate valid entity IDs matching NES format."""
    entity_types = ["person", "organization", "location"]
    entity_type = draw(st.sampled_from(entity_types))
    
    # Generate valid slug (ASCII lowercase letters, numbers, hyphens only)
    # NES validator expects: ^[a-z0-9]+(?:-[a-z0-9]+)*$
    slug = draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
        min_size=3,
        max_size=50
    ).filter(lambda x: x and not x.startswith("-") and not x.endswith("-") and "--" not in x))
    
    return f"entity:{entity_type}/{slug}"


@st.composite
def invalid_entity_id(draw):
    """Generate invalid entity IDs for negative testing."""
    invalid_formats = [
        draw(st.text(min_size=1, max_size=20)),  # Random text
        f"invalid:{draw(st.text(min_size=1, max_size=20))}",  # Wrong prefix
        f"entity:{draw(st.text(min_size=1, max_size=20))}",  # Missing slash
        "",  # Empty string
    ]
    return draw(st.sampled_from(invalid_formats))


@st.composite
def entity_id_list(draw, min_size=1, max_size=5):
    """Generate a list of valid entity IDs."""
    return draw(st.lists(valid_entity_id(), min_size=min_size, max_size=max_size))


@st.composite
def text_list(draw, min_size=1, max_size=5):
    """Generate a list of text strings."""
    return draw(st.lists(
        st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
        min_size=min_size,
        max_size=max_size
    ))


@st.composite
def timeline_entry(draw):
    """Generate a valid timeline entry."""
    import datetime
    return {
        "date": draw(st.dates(min_value=datetime.date(2000, 1, 1))).isoformat(),
        "title": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "description": draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip())),
    }


@st.composite
def timeline_list(draw, min_size=0, max_size=5):
    """Generate a list of timeline entries."""
    return draw(st.lists(timeline_entry(), min_size=min_size, max_size=max_size))


@st.composite
def evidence_entry(draw, source_ids):
    """Generate a valid evidence entry."""
    return {
        "source_id": draw(st.sampled_from(source_ids)) if source_ids else f"source:{draw(st.text(min_size=5, max_size=20))}",
        "description": draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip())),
    }


@st.composite
def evidence_list(draw, min_size=0, max_size=5):
    """Generate a list of evidence entries."""
    # Generate some source IDs first
    source_ids = [f"source:2024{i:04d}:abc{i}" for i in range(1, 6)]
    return draw(st.lists(
        evidence_entry(source_ids),
        min_size=min_size,
        max_size=max_size
    ))


# ============================================================================
# TextListField Tests
# ============================================================================

@settings(max_examples=100)
@given(texts=text_list(min_size=1, max_size=10))
def test_text_list_field_accepts_valid_text_list(texts):
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    For any list of text strings, TextListField should accept them without raising ValidationError.
    """
    field = TextListField()
    
    # Should not raise ValidationError
    try:
        field.validate(texts, None)
    except ValidationError:
        pytest.fail(f"TextListField rejected valid text list: {texts}")


def test_text_list_field_rejects_empty_strings():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    TextListField should reject lists containing empty strings.
    """
    field = TextListField()
    
    with pytest.raises(ValidationError):
        field.validate(["valid text", "", "another valid"], None)


def test_text_list_field_rejects_non_string_items():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    TextListField should reject lists containing non-string items.
    """
    field = TextListField()
    
    with pytest.raises(ValidationError):
        field.validate(["valid text", 123, "another valid"], None)


# ============================================================================
# TimelineListField Tests
# ============================================================================

@settings(max_examples=100)
@given(timeline=timeline_list(min_size=0, max_size=10))
def test_timeline_list_field_accepts_valid_timeline(timeline):
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    For any list of valid timeline entries, TimelineListField should accept them without raising ValidationError.
    """
    field = TimelineListField()
    
    # Should not raise ValidationError
    try:
        field.validate(timeline, None)
    except ValidationError:
        pytest.fail(f"TimelineListField rejected valid timeline: {timeline}")


def test_timeline_list_field_rejects_missing_required_fields():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    TimelineListField should reject entries missing required fields (date, title).
    Description is optional.
    """
    field = TimelineListField()
    
    # Missing 'date'
    with pytest.raises(ValidationError):
        field.validate([{"title": "Event", "description": "Description"}], None)
    
    # Missing 'title'
    with pytest.raises(ValidationError):
        field.validate([{"date": "2024-01-01", "description": "Description"}], None)


def test_timeline_list_field_rejects_invalid_date_format():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    TimelineListField should reject entries with invalid date formats.
    """
    field = TimelineListField()
    
    with pytest.raises(ValidationError):
        field.validate([{
            "date": "invalid-date",
            "title": "Event",
            "description": "Description"
        }], None)


def test_timeline_list_field_accepts_missing_description():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    TimelineListField should accept entries without description (description is optional).
    """
    field = TimelineListField()
    
    # Should not raise ValidationError
    try:
        field.validate([{
            "date": "2024-01-01",
            "title": "Event"
        }], None)
    except ValidationError as e:
        pytest.fail(f"TimelineListField should accept missing description, but raised: {e}")


def test_timeline_list_field_accepts_empty_description():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    TimelineListField should accept entries with empty description (description is optional).
    """
    field = TimelineListField()
    
    # Should not raise ValidationError
    try:
        field.validate([{
            "date": "2024-01-01",
            "title": "Event",
            "description": ""
        }], None)
    except ValidationError as e:
        pytest.fail(f"TimelineListField should accept empty description, but raised: {e}")


# ============================================================================
# EvidenceListField Tests
# ============================================================================

@settings(max_examples=100)
@given(evidence=evidence_list(min_size=0, max_size=10))
def test_evidence_list_field_accepts_valid_evidence(evidence):
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    For any list of valid evidence entries, EvidenceListField should accept them without raising ValidationError.
    """
    field = EvidenceListField()
    
    # Should not raise ValidationError
    try:
        field.validate(evidence, None)
    except ValidationError:
        pytest.fail(f"EvidenceListField rejected valid evidence: {evidence}")


def test_evidence_list_field_rejects_missing_required_fields():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    EvidenceListField should reject entries missing required fields (source_id, description).
    """
    field = EvidenceListField()
    
    # Missing 'source_id'
    with pytest.raises(ValidationError):
        field.validate([{"description": "Evidence description"}], None)
    
    # Missing 'description'
    with pytest.raises(ValidationError):
        field.validate([{"source_id": "source:20240115:abc123"}], None)


def test_evidence_list_field_rejects_empty_source_id():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    EvidenceListField should reject entries with empty source_id.
    """
    field = EvidenceListField()
    
    with pytest.raises(ValidationError):
        field.validate([{
            "source_id": "",
            "description": "Evidence description"
        }], None)
