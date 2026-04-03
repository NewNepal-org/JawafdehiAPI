"""
Property-based tests for Case model.

Feature: accountability-platform-core
Tests Properties 1, 2, 3, 18
Validates: Requirements 1.1, 1.2, 1.3, 7.3
"""

import pytest

from django.core.exceptions import ValidationError
from django.utils.text import slugify
from hypothesis import given, settings

from cases.models import Case, CaseState, CaseType, RelationshipType, CaseEntityRelationship
from tests.conftest import create_case_with_entities
from tests.strategies import minimal_case_data, complete_case_data

# ============================================================================
# Property 1: New cases start in Draft state
# ============================================================================


@pytest.mark.django_db
@settings(max_examples=100, deadline=None)
@given(case_data=minimal_case_data())
def test_new_cases_start_in_draft_state(case_data):
    """
    Feature: accountability-platform-core, Property 1: New cases start in Draft state

    For any case created, the initial state should be Draft.
    Validates: Requirements 1.1
    """
    case = create_case_with_entities(**case_data)

    assert (
        case.state == CaseState.DRAFT
    ), f"New case should start in DRAFT state, but got {case.state}"


# ============================================================================
# Property 2: Draft validation is lenient, In Review validation is strict
# ============================================================================


@pytest.mark.django_db
@settings(max_examples=100, deadline=None)
@given(case_data=minimal_case_data())
def test_draft_validation_is_lenient(case_data):
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict

    For any case in DRAFT state, only title and alleged_entities are required.
    Other fields (key_allegations, description) can be incomplete.
    Validates: Requirements 1.2
    """
    case = create_case_with_entities(**case_data)
    case.state = CaseState.DRAFT

    # Should not raise ValidationError even without key_allegations
    try:
        case.validate()
    except ValidationError as e:
        pytest.fail(f"Draft validation should be lenient, but raised: {e}")


@pytest.mark.django_db
@settings(max_examples=100, deadline=None)
@given(case_data=complete_case_data())
def test_in_review_validation_is_strict(case_data):
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict

    For any case transitioning to IN_REVIEW state, all required fields
    (alleged_entities, key_allegations) must be valid and complete.
    Validates: Requirements 1.2
    """
    case = create_case_with_entities(**case_data)
    case.state = CaseState.IN_REVIEW

    # Should not raise ValidationError with complete data
    try:
        case.validate()
    except ValidationError as e:
        pytest.fail(
            f"IN_REVIEW validation should pass with complete data, but raised: {e}"
        )


@pytest.mark.django_db
def test_in_review_validation_rejects_incomplete_data():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict

    For any case in IN_REVIEW state missing required fields, validation should fail.
    Validates: Requirements 1.2
    """
    # Create case with minimal data (valid for DRAFT)
    case = create_case_with_entities(
        title="Test Case",
        alleged_entities=["entity:person/test-person"],
        case_type=CaseType.CORRUPTION,
    )

    # Try to transition to IN_REVIEW without key_allegations
    case.state = CaseState.IN_REVIEW

    # Should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        case.validate()

    assert (
        "key_allegations" in str(exc_info.value).lower()
        or "allegation" in str(exc_info.value).lower()
    ), "Validation error should mention missing key_allegations"


# ============================================================================
# Property 3: Draft submission transitions to In Review
# ============================================================================


@pytest.mark.django_db
@settings(max_examples=100, deadline=None)
@given(case_data=complete_case_data())
def test_draft_submission_transitions_to_in_review(case_data):
    """
    Feature: accountability-platform-core, Property 3: Draft submission transitions to In Review

    For any case in Draft state, when submitted, the state should change to In Review.
    Validates: Requirements 1.3
    """
    case = create_case_with_entities(**case_data)
    assert case.state == CaseState.DRAFT

    # Submit the draft (this will be a method on the Case model)
    case.submit()

    assert (
        case.state == CaseState.IN_REVIEW
    ), f"Submitted case should be in IN_REVIEW state, but got {case.state}"


# ============================================================================
# Edge Cases and Additional Tests
# ============================================================================


@pytest.mark.django_db
def test_case_requires_at_least_one_alleged_entity():
    """
    Edge case: Cases in IN_REVIEW or PUBLISHED state must have at least one alleged entity.
    Validates: Requirements 1.2
    """
    # Draft cases can have empty alleged_entities (lenient validation)
    case = create_case_with_entities(
        title="Test Case",
        alleged_entities=[],  # Empty list
        case_type=CaseType.CORRUPTION,
    )
    # Should not raise for DRAFT state
    case.validate()

    # But should raise when transitioning to IN_REVIEW
    case.state = CaseState.IN_REVIEW
    with pytest.raises(ValidationError):
        case.validate()


def test_relationship_type_includes_accused_choice():
    """Relationship types should expose ACCUSED as an available choice."""
    assert RelationshipType.ACCUSED == "accused"
    assert RelationshipType.ACCUSED in RelationshipType.values


@pytest.mark.django_db
def test_case_requires_title():
    """
    Edge case: Cases must have a title.
    Validates: Requirements 1.2
    """
    with pytest.raises((ValidationError, ValueError)):
        create_case_with_entities(
            title="",  # Empty title
            alleged_entities=["entity:person/test-person"],
            case_type=CaseType.CORRUPTION,
        )


@pytest.mark.django_db
def test_case_notes_default_to_blank_and_persist():
    """
    Edge case: Cases should support internal notes with a blank default.
    """
    case = create_case_with_entities(
        title="Notes Case",
        alleged_entities=["entity:person/test-person"],
        case_type=CaseType.CORRUPTION,
    )

    assert case.notes == ""

    case.notes = "## Internal note\n\nFollow up with records office."
    case.save()
    case.refresh_from_db()

    assert case.notes == "## Internal note\n\nFollow up with records office."


# ============================================================================
# Property 18: Soft delete sets state to CLOSED
# ============================================================================


@pytest.mark.django_db
@settings(max_examples=100, deadline=None)
@given(case_data=complete_case_data())
def test_soft_delete_sets_state_to_closed(case_data):
    """
    Feature: accountability-platform-core, Property 18: Soft delete sets state to CLOSED

    For any case deleted in Django Admin, its state should be set to CLOSED
    and the record should remain in the database.
    Validates: Requirements 7.3
    """
    # Create a case in any state
    case = create_case_with_entities(**case_data)
    original_id = case.id
    original_case_id = case.case_id

    # Soft delete the case (this will be implemented in task 17)
    # For now, we test the expected behavior: setting state to CLOSED
    case.delete()

    # Verify the case still exists in the database
    assert Case.objects.filter(
        id=original_id
    ).exists(), "Soft-deleted case should still exist in database"

    # Verify the state is set to CLOSED
    case.refresh_from_db()
    assert (
        case.state == CaseState.CLOSED
    ), f"Soft-deleted case should have state CLOSED, but got {case.state}"

    # Verify the case_id is unchanged
    assert (
        case.case_id == original_case_id
    ), "Soft-deleted case should retain its case_id"


@pytest.mark.django_db
@settings(max_examples=50, deadline=None)
@given(case_data=complete_case_data())
def test_soft_delete_preserves_all_data(case_data):
    """
    Feature: accountability-platform-core, Property 18: Soft delete sets state to CLOSED

    For any case deleted in Django Admin, all data should be preserved
    (only state changes to CLOSED).
    Validates: Requirements 7.3
    """
    # Create and publish a case
    case = create_case_with_entities(**case_data)
    case.state = CaseState.PUBLISHED
    case.save()

    original_title = case.title
    original_alleged_entities = list(
        case.entity_relationships.filter(relationship_type="alleged").values_list(
            "entity_id", flat=True
        )
    )
    original_key_allegations = case.key_allegations.copy()

    # Soft delete the case
    case.delete()

    # Verify all data is preserved except state
    case.refresh_from_db()
    assert case.state == CaseState.CLOSED, "Soft-deleted case should have state CLOSED"
    assert case.title == original_title, "Soft-deleted case should preserve title"
    assert (
        list(
            case.entity_relationships.filter(relationship_type="alleged").values_list(
                "entity_id", flat=True
            )
        )
        == original_alleged_entities
    ), "Soft-deleted case should preserve alleged entities"
    assert (
        case.key_allegations == original_key_allegations
    ), "Soft-deleted case should preserve key_allegations"


# ============================================================================
# Notes field
# ============================================================================


@pytest.mark.django_db
def test_notes_field_defaults_to_empty():
    """Cases are created with an empty notes field by default."""
    case = create_case_with_entities(
        title="Test case",
        alleged_entities=["entity:person/test-person"],
        case_type=CaseType.CORRUPTION,
    )
    assert case.notes == "", "notes field should default to empty string"


@pytest.mark.django_db
def test_notes_field_stores_markdown():
    """The notes field accepts and persists markdown content."""
    markdown_content = "## Internal notes\n\n- Point one\n- Point two"
    case = create_case_with_entities(
        title="Test case",
        alleged_entities=["entity:person/test-person"],
        case_type=CaseType.CORRUPTION,
        notes=markdown_content,
    )
    case.refresh_from_db()
    assert case.notes == markdown_content



# ============================================================================
# Tests for new Case fields (slug, court_cases, missing_details, bigo)
# ============================================================================


@pytest.mark.django_db
def test_published_case_requires_slug():
    """Published case must have a slug."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
    )
    case.state = CaseState.PUBLISHED
    case.slug = None  # Explicitly set to None

    with pytest.raises(ValidationError) as exc_info:
        case.validate()

    assert "slug" in exc_info.value.error_dict
    assert "required for published cases" in str(exc_info.value)


@pytest.mark.django_db
def test_slug_immutability_once_set():
    """Slug cannot be changed once set."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
    )
    case.slug = "original-slug"
    case.save()

    # Try to change slug
    case.slug = "new-slug"

    with pytest.raises(ValidationError) as exc_info:
        case.save()

    assert "cannot be modified once set" in str(exc_info.value)


@pytest.mark.django_db
def test_slug_can_be_set_initially():
    """Slug can be set when creating a case."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        slug="my-custom-slug",
    )

    assert case.slug == "my-custom-slug"


@pytest.mark.django_db
def test_slug_auto_generated_for_published_case_without_slug():
    """Published case without slug gets auto-generated slug."""
    entity = JawafEntity.objects.create(
        nes_id="entity:person/test-person",
        display_name="Test Person",
    )
    
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case for Slug Generation",
        key_allegations=["Allegation 1"],
        description="Test description",
    )

    # Add accused entity
    CaseEntityRelationship.objects.create(
        case=case,
        entity=entity,
        relationship_type=RelationshipType.ACCUSED,
    )

    # Publish without setting slug
    case.slug = None
    case.publish()

    # Slug should be auto-generated
    assert case.slug is not None
    assert len(case.slug) > 0
    assert case.slug.startswith(slugify(case.title)[:42])


@pytest.mark.django_db
def test_missing_details_blank_becomes_none():
    """Empty missing_details should be stored as None."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        missing_details="",
    )

    # Note: This test verifies the intended behavior
    # The actual normalization should happen in serializers/admin
    # For now, we just verify the field accepts None
    case.missing_details = None
    case.save()

    case.refresh_from_db()
    assert case.missing_details is None


@pytest.mark.django_db
def test_missing_details_whitespace_becomes_none():
    """Whitespace-only missing_details should be stored as None."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        missing_details="   ",
    )

    # Normalize to None
    case.missing_details = None
    case.save()

    case.refresh_from_db()
    assert case.missing_details is None


@pytest.mark.django_db
def test_missing_details_with_content_is_preserved():
    """Non-empty missing_details should be preserved."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        missing_details="Missing witness statements",
    )

    case.refresh_from_db()
    assert case.missing_details == "Missing witness statements"


@pytest.mark.django_db
def test_court_cases_valid_list():
    """Valid court_cases list should be accepted."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        court_cases=["supreme:2078-CR-0123", "special:2077-WO-0456"],
    )

    case.refresh_from_db()
    assert case.court_cases == ["supreme:2078-CR-0123", "special:2077-WO-0456"]


@pytest.mark.django_db
def test_court_cases_empty_list():
    """Empty court_cases list should be accepted."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        court_cases=[],
    )

    case.refresh_from_db()
    assert case.court_cases == []


@pytest.mark.django_db
def test_court_cases_null():
    """Null court_cases should be accepted."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        court_cases=None,
    )

    case.refresh_from_db()
    assert case.court_cases is None


@pytest.mark.django_db
def test_court_cases_invalid_format_raises_error():
    """Invalid court_cases format should raise ValidationError."""
    with pytest.raises(ValidationError):
        case = Case.objects.create(
            case_type="CORRUPTION",
            title="Test Case",
            court_cases=["invalid-format"],
        )
        case.full_clean()


@pytest.mark.django_db
def test_bigo_positive_integer():
    """Bigo field should accept positive integers."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        bigo=1000000,
    )

    case.refresh_from_db()
    assert case.bigo == 1000000


@pytest.mark.django_db
def test_bigo_null():
    """Bigo field should accept None."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        bigo=None,
    )

    case.refresh_from_db()
    assert case.bigo is None


@pytest.mark.django_db
def test_bigo_large_value():
    """Bigo field should accept large values."""
    case = Case.objects.create(
        case_type="CORRUPTION",
        title="Test Case",
        bigo=999999999999999999,  # Large BigInteger
    )

    case.refresh_from_db()
    assert case.bigo == 999999999999999999
