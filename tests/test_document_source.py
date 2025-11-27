"""
Property-based tests for DocumentSource model.

Feature: accountability-platform-core
Property 11: Source validation enforces required fields
Validates: Requirements 4.2
"""

import pytest
from hypothesis import given, strategies as st, settings
from django.core.exceptions import ValidationError

# Import will work once DocumentSource model is implemented in task 6
try:
    from cases.models import DocumentSource
except ImportError:
    pytest.skip("DocumentSource model not yet implemented", allow_module_level=True)


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
def entity_id_list(draw, min_size=0, max_size=5):
    """Generate a list of valid entity IDs."""
    return draw(st.lists(valid_entity_id(), min_size=min_size, max_size=max_size, unique=True))


@st.composite
def valid_source_data(draw):
    """
    Generate valid DocumentSource data with all required fields.
    
    According to Property 11 and Requirement 4.2, required fields are:
    - title
    - description
    """
    return {
        "title": draw(st.text(min_size=1, max_size=300).filter(lambda x: x.strip())),
        "description": draw(st.text(min_size=1, max_size=1000).filter(lambda x: x.strip())),
        "related_entity_ids": draw(entity_id_list(min_size=0, max_size=3)),
        "url": draw(st.one_of(
            st.none(),
            st.from_regex(r'https?://[a-z0-9\-\.]+\.[a-z]{2,}(/[^\s]*)?', fullmatch=True)
        )),
    }


@st.composite
def source_data_missing_title(draw):
    """Generate DocumentSource data missing the title field."""
    data = draw(valid_source_data())
    del data["title"]
    return data


@st.composite
def source_data_missing_description(draw):
    """Generate DocumentSource data missing the description field."""
    data = draw(valid_source_data())
    del data["description"]
    return data


@st.composite
def source_data_with_empty_title(draw):
    """Generate DocumentSource data with empty title."""
    data = draw(valid_source_data())
    data["title"] = ""
    return data


@st.composite
def source_data_with_empty_description(draw):
    """Generate DocumentSource data with empty description."""
    data = draw(valid_source_data())
    data["description"] = ""
    return data


# ============================================================================
# Property 11: Source validation enforces required fields
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=100)
@given(source_data=valid_source_data())
def test_document_source_accepts_valid_data(source_data):
    """
    Feature: accountability-platform-core, Property 11: Source validation enforces required fields
    
    For any DocumentSource with all required fields (title, description),
    validation should pass without raising ValidationError.
    Validates: Requirements 4.2
    """
    source = DocumentSource(**source_data)
    source.save()
    
    # Should not raise ValidationError
    try:
        source.validate()
    except ValidationError as e:
        pytest.fail(f"DocumentSource validation rejected valid data: {e}")


@pytest.mark.django_db
@settings(max_examples=100)
@given(source_data=source_data_missing_title())
def test_document_source_rejects_missing_title(source_data):
    """
    Feature: accountability-platform-core, Property 11: Source validation enforces required fields
    
    For any DocumentSource creation attempt missing title,
    the Platform should reject the operation.
    Validates: Requirements 4.2
    """
    # Should raise ValidationError when missing title
    with pytest.raises(ValidationError) as exc_info:
        source = DocumentSource(**source_data)
        source.save()
        source.validate()
    
    # Verify error mentions title
    error_message = str(exc_info.value).lower()
    assert "title" in error_message, \
        f"Validation error should mention 'title', but got: {exc_info.value}"


@pytest.mark.django_db
@settings(max_examples=100)
@given(source_data=source_data_missing_description())
def test_document_source_accepts_missing_description(source_data):
    """
    Feature: accountability-platform-core, Property 11: Source validation enforces required fields
    
    For any DocumentSource creation attempt missing description,
    the Platform should accept it (description is optional).
    Validates: Requirements 4.2
    """
    # Should not raise ValidationError when missing description
    source = DocumentSource(**source_data)
    source.save()
    
    try:
        source.validate()
    except ValidationError as e:
        pytest.fail(f"DocumentSource should accept missing description, but raised: {e}")


@pytest.mark.django_db
@settings(max_examples=50)
@given(source_data=source_data_with_empty_title())
def test_document_source_rejects_empty_title(source_data):
    """
    Feature: accountability-platform-core, Property 11: Source validation enforces required fields
    
    For any DocumentSource with empty title (whitespace only),
    the Platform should reject the operation.
    Validates: Requirements 4.2
    """
    # Should raise ValidationError when title is empty
    with pytest.raises(ValidationError):
        source = DocumentSource(**source_data)
        source.save()


@pytest.mark.django_db
@settings(max_examples=50)
@given(source_data=source_data_with_empty_description())
def test_document_source_accepts_empty_description(source_data):
    """
    Feature: accountability-platform-core, Property 11: Source validation enforces required fields
    
    For any DocumentSource with empty description (whitespace only),
    the Platform should accept it (description is optional).
    Validates: Requirements 4.2
    """
    # Should not raise ValidationError when description is empty
    source = DocumentSource(**source_data)
    source.save()
    
    try:
        source.validate()
    except ValidationError as e:
        pytest.fail(f"DocumentSource should accept empty description, but raised: {e}")


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.django_db
def test_document_source_requires_title():
    """
    Edge case: DocumentSource must have a non-empty title.
    Validates: Requirements 4.2
    """
    with pytest.raises(ValidationError):
        source = DocumentSource(
            description="Valid description",
            related_entity_ids=[]
        )
        source.save()


@pytest.mark.django_db
def test_document_source_accepts_missing_description():
    """
    Edge case: DocumentSource can be created without description (description is optional).
    Validates: Requirements 4.2
    """
    source = DocumentSource(
        title="Valid Title",
        related_entity_ids=[]
    )
    source.save()
    
    # Should not raise ValidationError without description
    try:
        source.validate()
    except ValidationError as e:
        pytest.fail(f"DocumentSource should allow missing description, but raised: {e}")


@pytest.mark.django_db
def test_document_source_url_is_optional():
    """
    Edge case: URL field is optional for DocumentSource.
    Validates: Requirements 4.1, 4.2
    """
    source = DocumentSource(
        title="Valid Title",
        description="Valid description",
        related_entity_ids=[]
    )
    source.save()
    
    # Should not raise ValidationError without URL
    try:
        source.validate()
    except ValidationError as e:
        pytest.fail(f"DocumentSource should allow missing URL, but raised: {e}")


@pytest.mark.django_db
def test_document_source_soft_deletion():
    """
    Edge case: DocumentSource should support soft deletion via is_deleted flag.
    Validates: Design document soft deletion requirement
    """
    source = DocumentSource(
        title="Valid Title",
        description="Valid description",
        related_entity_ids=[]
    )
    source.save()
    
    # Soft delete
    source.is_deleted = True
    source.save()
    
    # Should still exist in database
    assert DocumentSource.objects.filter(id=source.id).exists(), \
        "Soft-deleted source should still exist in database"
    
    # Verify is_deleted flag is set
    source.refresh_from_db()
    assert source.is_deleted is True, \
        "is_deleted flag should be True after soft deletion"


@pytest.mark.django_db
def test_document_source_has_contributors_field():
    """
    Edge case: DocumentSource should have a contributors ManyToMany field.
    Validates: Design document - sources have contributors for access control
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Create a user
    user = User.objects.create_user(username='testuser', password='test123')
    
    # Create a source
    source = DocumentSource(
        title="Valid Title",
        description="Valid description",
        related_entity_ids=[]
    )
    source.save()
    
    # Add contributor
    source.contributors.add(user)
    
    # Verify contributor is assigned
    assert user in source.contributors.all(), \
        "User should be in source contributors"
    
    # Verify reverse relationship
    assert source in user.assigned_sources.all(), \
        "Source should be in user's assigned_sources"
