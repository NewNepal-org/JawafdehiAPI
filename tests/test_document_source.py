"""
Property-based tests for DocumentSource model.

Feature: accountability-platform-core
Property 11: Source validation enforces required fields
Validates: Requirements 4.2
"""

import pytest

from django.core.exceptions import ValidationError
from hypothesis import given, settings

from cases.models import DocumentSource
from tests.conftest import create_document_source_with_entities
from tests.strategies import (
    valid_source_data,
    source_data_missing_title,
    source_data_missing_description,
    source_data_with_empty_title,
    source_data_with_empty_description,
)


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
    source = create_document_source_with_entities(**source_data)
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
        source = create_document_source_with_entities(**source_data)
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
    source = create_document_source_with_entities(**source_data)
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
        source = create_document_source_with_entities(**source_data)
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
    source = create_document_source_with_entities(**source_data)
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
        source = create_document_source_with_entities(
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
    source = create_document_source_with_entities(
        title="Valid Title",
        related_entity_ids=[],
        urls=["https://example.com"]
    )
    source.save()
    
    # Should not raise ValidationError without description
    try:
        source.validate()
    except ValidationError as e:
        pytest.fail(f"DocumentSource should allow missing description, but raised: {e}")


@pytest.mark.django_db
def test_document_source_requires_at_least_one_url():
    """
    Edge case: At least one URL is required for DocumentSource.
    Validates: Requirements 4.1, 4.2
    """
    # Test that creating a source without URLs raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        source = create_document_source_with_entities(
            title="Valid Title",
            description="Valid description",
            related_entity_ids=[],
            urls=[]
        )
        source.save()
    
    # Verify error mentions URLs
    error_message = str(exc_info.value).lower()
    assert "url" in error_message, \
        f"Validation error should mention 'url', but got: {exc_info.value}"
    
    # Test that creating a source with at least one URL works
    source = create_document_source_with_entities(
        title="Valid Title",
        description="Valid description",
        related_entity_ids=[],
        urls=["https://example.com"]
    )
    source.save()
    
    # Should not raise ValidationError with URL
    try:
        source.validate()
    except ValidationError as e:
        pytest.fail(f"DocumentSource should accept at least one URL, but raised: {e}")



@pytest.mark.django_db
def test_document_source_soft_deletion():
    """
    Edge case: DocumentSource should support soft deletion via is_deleted flag.
    Validates: Design document soft deletion requirement
    """
    source = create_document_source_with_entities(
        title="Valid Title",
        description="Valid description",
        related_entity_ids=[],
        urls=["https://example.com"]
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
    source = create_document_source_with_entities(
        title="Valid Title",
        description="Valid description",
        related_entity_ids=[],
        urls=["https://example.com"]
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
