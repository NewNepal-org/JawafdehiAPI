"""
Property-based tests for Case model.

Feature: accountability-platform-core
Tests Properties 1, 2, 3, 3a, 4, 18
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 7.3
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

# Import will work once Case model is implemented in task 4
try:
    from cases.models import Case, CaseState, CaseType
except ImportError:
    pytest.skip("Case model not yet implemented", allow_module_level=True)


User = get_user_model()


# ============================================================================
# Hypothesis Strategies (Generators)
# ============================================================================

@st.composite
def valid_entity_id(draw):
    """Generate valid entity IDs matching NES format."""
    entity_types = ["person", "organization", "location"]
    entity_type = draw(st.sampled_from(entity_types))
    
    # Generate valid slug (lowercase letters, numbers, hyphens)
    slug = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        min_size=3,
        max_size=50
    ).filter(lambda x: x and not x.startswith("-") and not x.endswith("-")))
    
    return f"entity:{entity_type}/{slug}"


@st.composite
def entity_id_list(draw, min_size=1, max_size=5):
    """Generate a list of valid entity IDs."""
    return draw(st.lists(valid_entity_id(), min_size=min_size, max_size=max_size, unique=True))


@st.composite
def text_list(draw, min_size=1, max_size=5):
    """Generate a list of text strings."""
    return draw(st.lists(
        st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
        min_size=min_size,
        max_size=max_size
    ))


@st.composite
def minimal_case_data(draw):
    """
    Generate minimal valid case data for DRAFT state.
    
    According to Property 2, draft validation is lenient - only title and
    at least one alleged entity are required.
    """
    return {
        "title": draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip())),
        "alleged_entities": draw(entity_id_list(min_size=1, max_size=3)),
        "case_type": draw(st.sampled_from([CaseType.CORRUPTION, CaseType.PROMISES])),
    }


@st.composite
def complete_case_data(draw):
    """
    Generate complete valid case data for IN_REVIEW state.
    
    According to Property 2, IN_REVIEW validation is strict - all required
    fields must be present and valid.
    """
    return {
        "title": draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip())),
        "alleged_entities": draw(entity_id_list(min_size=1, max_size=3)),
        "key_allegations": draw(text_list(min_size=1, max_size=5)),
        "case_type": draw(st.sampled_from([CaseType.CORRUPTION, CaseType.PROMISES])),
        "description": draw(st.text(min_size=10, max_size=1000).filter(lambda x: x.strip())),
    }


# ============================================================================
# Property 1: New cases start in Draft state
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=100)
@given(case_data=minimal_case_data())
def test_new_cases_start_in_draft_state(case_data):
    """
    Feature: accountability-platform-core, Property 1: New cases start in Draft state
    
    For any case created, the initial state should be Draft.
    Validates: Requirements 1.1
    """
    case = Case.objects.create(**case_data)
    
    assert case.state == CaseState.DRAFT, \
        f"New case should start in DRAFT state, but got {case.state}"
    assert case.version == 1, \
        f"New case should start at version 1, but got {case.version}"


# ============================================================================
# Property 2: Draft validation is lenient, In Review validation is strict
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=100)
@given(case_data=minimal_case_data())
def test_draft_validation_is_lenient(case_data):
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    For any case in DRAFT state, only title and alleged_entities are required.
    Other fields (key_allegations, description) can be incomplete.
    Validates: Requirements 1.2
    """
    case = Case.objects.create(**case_data)
    case.state = CaseState.DRAFT
    
    # Should not raise ValidationError even without key_allegations
    try:
        case.validate()
    except ValidationError as e:
        pytest.fail(f"Draft validation should be lenient, but raised: {e}")


@pytest.mark.django_db
@settings(max_examples=100)
@given(case_data=complete_case_data())
def test_in_review_validation_is_strict(case_data):
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    For any case transitioning to IN_REVIEW state, all required fields
    (alleged_entities, key_allegations) must be valid and complete.
    Validates: Requirements 1.2
    """
    case = Case.objects.create(**case_data)
    case.state = CaseState.IN_REVIEW
    
    # Should not raise ValidationError with complete data
    try:
        case.validate()
    except ValidationError as e:
        pytest.fail(f"IN_REVIEW validation should pass with complete data, but raised: {e}")


@pytest.mark.django_db
def test_in_review_validation_rejects_incomplete_data():
    """
    Feature: accountability-platform-core, Property 2: Draft validation is lenient, In Review validation is strict
    
    For any case in IN_REVIEW state missing required fields, validation should fail.
    Validates: Requirements 1.2
    """
    # Create case with minimal data (valid for DRAFT)
    case = Case.objects.create(
        title="Test Case",
        alleged_entities=["entity:person/test-person"],
        case_type=CaseType.CORRUPTION,
    )
    
    # Try to transition to IN_REVIEW without key_allegations
    case.state = CaseState.IN_REVIEW
    
    # Should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        case.validate()
    
    assert "key_allegations" in str(exc_info.value).lower() or \
           "allegation" in str(exc_info.value).lower(), \
           "Validation error should mention missing key_allegations"


# ============================================================================
# Property 3: Draft submission transitions to In Review
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=100)
@given(case_data=complete_case_data())
def test_draft_submission_transitions_to_in_review(case_data):
    """
    Feature: accountability-platform-core, Property 3: Draft submission transitions to In Review
    
    For any case in Draft state, when submitted, the state should change to In Review.
    Validates: Requirements 1.3
    """
    case = Case.objects.create(**case_data)
    assert case.state == CaseState.DRAFT
    
    # Submit the draft (this will be a method on the Case model)
    case.submit()
    
    assert case.state == CaseState.IN_REVIEW, \
        f"Submitted case should be in IN_REVIEW state, but got {case.state}"


# ============================================================================
# Property 3a: Draft creation increments version
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=50)
@given(case_data=complete_case_data())
def test_draft_creation_increments_version(case_data):
    """
    Feature: accountability-platform-core, Property 3a: Draft creation increments version
    
    For any published case, when create_draft() is called, the new draft
    should have version incremented by 1.
    Validates: Requirements 1.4
    """
    # Create and publish a case
    case = Case.objects.create(**case_data)
    case.state = CaseState.PUBLISHED
    case.save()
    
    original_version = case.version
    original_case_id = case.case_id
    
    # Create a draft from the published case
    draft = case.create_draft()
    
    assert draft.case_id == original_case_id, \
        f"Draft should have same case_id as original, but got {draft.case_id} vs {original_case_id}"
    assert draft.version == original_version + 1, \
        f"Draft version should be {original_version + 1}, but got {draft.version}"
    assert draft.state == CaseState.DRAFT, \
        f"New draft should be in DRAFT state, but got {draft.state}"
    
    # Original should remain unchanged
    case.refresh_from_db()
    assert case.state == CaseState.PUBLISHED, \
        "Original case should remain PUBLISHED"
    assert case.version == original_version, \
        "Original case version should not change"


# ============================================================================
# Property 4: Editing published cases preserves original
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=50)
@given(case_data=complete_case_data())
def test_editing_published_cases_preserves_original(case_data):
    """
    Feature: accountability-platform-core, Property 4: Editing published cases preserves original
    
    For any published case, when a Contributor edits it, a new draft revision
    should be created and the published version should remain unchanged.
    Validates: Requirements 1.4
    """
    # Create and publish a case
    case = Case.objects.create(**case_data)
    case.state = CaseState.PUBLISHED
    case.save()
    
    original_title = case.title
    original_case_id = case.case_id
    original_version = case.version
    original_id = case.id
    
    # Create a draft for editing
    draft = case.create_draft()
    
    # Modify the draft
    new_title = f"{original_title} - Modified"
    draft.title = new_title
    draft.save()
    
    # Verify draft has changes
    assert draft.title == new_title, \
        "Draft should have the modified title"
    assert draft.state == CaseState.DRAFT, \
        "Draft should be in DRAFT state"
    assert draft.case_id == original_case_id, \
        "Draft should have same case_id"
    assert draft.id != original_id, \
        "Draft should be a new database record"
    
    # Verify original is preserved
    case.refresh_from_db()
    assert case.title == original_title, \
        "Original case title should be unchanged"
    assert case.state == CaseState.PUBLISHED, \
        "Original case should remain PUBLISHED"
    assert case.version == original_version, \
        "Original case version should be unchanged"
    assert case.id == original_id, \
        "Original case should be the same database record"


# ============================================================================
# Edge Cases and Additional Tests
# ============================================================================

@pytest.mark.django_db
def test_case_requires_at_least_one_alleged_entity():
    """
    Edge case: Cases must have at least one alleged entity.
    Validates: Requirements 1.2
    """
    with pytest.raises((ValidationError, ValueError)):
        case = Case.objects.create(
            title="Test Case",
            alleged_entities=[],  # Empty list
            case_type=CaseType.CORRUPTION,
        )
        case.validate()


@pytest.mark.django_db
def test_case_requires_title():
    """
    Edge case: Cases must have a title.
    Validates: Requirements 1.2
    """
    with pytest.raises((ValidationError, ValueError)):
        Case.objects.create(
            title="",  # Empty title
            alleged_entities=["entity:person/test-person"],
            case_type=CaseType.CORRUPTION,
        )


# ============================================================================
# Property 18: Soft delete sets state to CLOSED
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=100)
@given(case_data=complete_case_data())
def test_soft_delete_sets_state_to_closed(case_data):
    """
    Feature: accountability-platform-core, Property 18: Soft delete sets state to CLOSED
    
    For any case deleted in Django Admin, its state should be set to CLOSED
    and the record should remain in the database.
    Validates: Requirements 7.3
    """
    # Create a case in any state
    case = Case.objects.create(**case_data)
    original_id = case.id
    original_case_id = case.case_id
    
    # Soft delete the case (this will be implemented in task 17)
    # For now, we test the expected behavior: setting state to CLOSED
    case.delete()
    
    # Verify the case still exists in the database
    assert Case.objects.filter(id=original_id).exists(), \
        "Soft-deleted case should still exist in database"
    
    # Verify the state is set to CLOSED
    case.refresh_from_db()
    assert case.state == CaseState.CLOSED, \
        f"Soft-deleted case should have state CLOSED, but got {case.state}"
    
    # Verify the case_id is unchanged
    assert case.case_id == original_case_id, \
        "Soft-deleted case should retain its case_id"


@pytest.mark.django_db
@settings(max_examples=50)
@given(case_data=complete_case_data())
def test_soft_delete_preserves_all_data(case_data):
    """
    Feature: accountability-platform-core, Property 18: Soft delete sets state to CLOSED
    
    For any case deleted in Django Admin, all data should be preserved
    (only state changes to CLOSED).
    Validates: Requirements 7.3
    """
    # Create and publish a case
    case = Case.objects.create(**case_data)
    case.state = CaseState.PUBLISHED
    case.save()
    
    original_id = case.id
    original_title = case.title
    original_version = case.version
    original_alleged_entities = case.alleged_entities.copy()
    original_key_allegations = case.key_allegations.copy()
    
    # Soft delete the case
    case.delete()
    
    # Verify all data is preserved except state
    case.refresh_from_db()
    assert case.state == CaseState.CLOSED, \
        "Soft-deleted case should have state CLOSED"
    assert case.title == original_title, \
        "Soft-deleted case should preserve title"
    assert case.version == original_version, \
        "Soft-deleted case should preserve version"
    assert case.alleged_entities == original_alleged_entities, \
        "Soft-deleted case should preserve alleged_entities"
    assert case.key_allegations == original_key_allegations, \
        "Soft-deleted case should preserve key_allegations"
