"""
Preservation Property Tests for Entity Schema Serialization Fix

These tests capture the current behavior for non-entity fields that must be preserved
during the entity schema serialization fix. These tests should PASS on unfixed code
to establish the baseline behavior.

**IMPORTANT**: These tests follow observation-first methodology - they observe and
capture the current behavior on UNFIXED code, then ensure it remains unchanged after the fix.

Feature: entity-schema-serialization-fix
Property 2: Preservation - Non-Entity Field Serialization Unchanged
Validates: Requirements 3.1, 3.2, 3.3
"""

import pytest
from hypothesis import given, settings
from rest_framework.test import APIClient

from cases.models import CaseState, CaseType, CaseEntityRelationship, RelationshipType
from tests.conftest import create_case_with_entities, create_entities_from_ids
from tests.strategies import complete_case_data_with_timeline as complete_case_data


@pytest.mark.django_db
def test_preservation_case_metadata_fields():
    """
    Preservation Test: Case metadata fields should serialize identically after fix

    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)

    This test captures the current serialization behavior for non-entity case fields
    like title, description, case_type, state, etc.
    """
    # Create a case with comprehensive metadata
    case = create_case_with_entities(
        title="Preservation Test Case",
        case_type=CaseType.CORRUPTION,
        description="<p>Test case for preservation of metadata fields during entity schema fix.</p>",
        key_allegations=["Preservation allegation 1", "Preservation allegation 2"],
        state=CaseState.PUBLISHED,
    )

    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")

    assert (
        response.status_code == 200
    ), f"API should return 200 OK, got {response.status_code}"

    case_data = response.data

    # Test preservation of core metadata fields
    assert "id" in case_data, "Response should include 'id' field"
    assert isinstance(
        case_data["id"], int
    ), f"id should be integer, got {type(case_data['id'])}: {case_data['id']}"
    assert (
        case_data["id"] == case.id
    ), f"id should match case.id ({case.id}), got {case_data['id']}"

    assert "case_id" in case_data, "Response should include 'case_id' field"
    assert isinstance(
        case_data["case_id"], str
    ), f"case_id should be string, got {type(case_data['case_id'])}: {case_data['case_id']}"
    assert (
        case_data["case_id"] == case.case_id
    ), f"case_id should match case.case_id ({case.case_id}), got {case_data['case_id']}"

    assert "title" in case_data, "Response should include 'title' field"
    assert isinstance(
        case_data["title"], str
    ), f"title should be string, got {type(case_data['title'])}: {case_data['title']}"
    assert (
        case_data["title"] == case.title
    ), f"title should match case.title ({case.title}), got {case_data['title']}"

    assert "case_type" in case_data, "Response should include 'case_type' field"
    assert isinstance(
        case_data["case_type"], str
    ), f"case_type should be string, got {type(case_data['case_type'])}: {case_data['case_type']}"
    assert (
        case_data["case_type"] == case.case_type.value
    ), f"case_type should match case.case_type ({case.case_type.value}), got {case_data['case_type']}"

    assert "state" in case_data, "Response should include 'state' field"
    assert isinstance(
        case_data["state"], str
    ), f"state should be string, got {type(case_data['state'])}: {case_data['state']}"
    assert (
        case_data["state"] == case.state.value
    ), f"state should match case.state ({case.state.value}), got {case_data['state']}"

    assert "description" in case_data, "Response should include 'description' field"
    assert isinstance(
        case_data["description"], str
    ), f"description should be string, got {type(case_data['description'])}: {case_data['description']}"
    assert (
        case_data["description"] == case.description
    ), f"description should match case.description, got {case_data['description']}"

    assert (
        "key_allegations" in case_data
    ), "Response should include 'key_allegations' field"
    assert isinstance(
        case_data["key_allegations"], list
    ), f"key_allegations should be list, got {type(case_data['key_allegations'])}: {case_data['key_allegations']}"
    assert (
        case_data["key_allegations"] == case.key_allegations
    ), f"key_allegations should match case.key_allegations, got {case_data['key_allegations']}"


@pytest.mark.django_db
def test_preservation_timestamp_fields():
    """
    Preservation Test: Timestamp fields should maintain format and values after fix

    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)

    This test captures the current serialization behavior for timestamp fields.
    """
    # Create a case
    case = create_case_with_entities(
        title="Timestamp Preservation Test",
        case_type=CaseType.CORRUPTION,
        description="Test case for timestamp preservation",
        key_allegations=["Timestamp test allegation"],
        state=CaseState.PUBLISHED,
    )

    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")

    assert response.status_code == 200
    case_data = response.data

    # Test timestamp field preservation
    assert "created_at" in case_data, "Response should include 'created_at' field"
    assert isinstance(
        case_data["created_at"], str
    ), f"created_at should be string, got {type(case_data['created_at'])}: {case_data['created_at']}"
    # Verify it's a valid ISO datetime string format
    from datetime import datetime

    try:
        datetime.fromisoformat(case_data["created_at"].replace("Z", "+00:00"))
    except ValueError:
        assert (
            False
        ), f"created_at should be valid ISO datetime string, got {case_data['created_at']}"

    assert "updated_at" in case_data, "Response should include 'updated_at' field"
    assert isinstance(
        case_data["updated_at"], str
    ), f"updated_at should be string, got {type(case_data['updated_at'])}: {case_data['updated_at']}"
    # Verify it's a valid ISO datetime string format
    try:
        datetime.fromisoformat(case_data["updated_at"].replace("Z", "+00:00"))
    except ValueError:
        assert (
            False
        ), f"updated_at should be valid ISO datetime string, got {case_data['updated_at']}"


@pytest.mark.django_db
def test_preservation_array_fields():
    """
    Preservation Test: Array fields (timeline, evidence) should maintain structure after fix

    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)

    This test captures the current serialization behavior for array fields.
    """
    # Create a case with array data
    case = create_case_with_entities(
        title="Array Fields Preservation Test",
        case_type=CaseType.CORRUPTION,
        description="Test case for array field preservation",
        key_allegations=["Array test allegation 1", "Array test allegation 2"],
        state=CaseState.PUBLISHED,
    )

    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")

    assert response.status_code == 200
    case_data = response.data

    # Test array field preservation
    assert "timeline" in case_data, "Response should include 'timeline' field"
    assert isinstance(
        case_data["timeline"], list
    ), f"timeline should be list, got {type(case_data['timeline'])}: {case_data['timeline']}"
    # Timeline is typically empty for new cases, but structure should be preserved

    assert "evidence" in case_data, "Response should include 'evidence' field"
    assert isinstance(
        case_data["evidence"], list
    ), f"evidence should be list, got {type(case_data['evidence'])}: {case_data['evidence']}"
    # Evidence is typically empty for new cases, but structure should be preserved

    assert "tags" in case_data, "Response should include 'tags' field"
    assert isinstance(
        case_data["tags"], list
    ), f"tags should be list, got {type(case_data['tags'])}: {case_data['tags']}"

    # key_allegations should be preserved as tested in metadata test
    assert (
        "key_allegations" in case_data
    ), "Response should include 'key_allegations' field"
    assert isinstance(
        case_data["key_allegations"], list
    ), f"key_allegations should be list, got {type(case_data['key_allegations'])}: {case_data['key_allegations']}"
    assert (
        len(case_data["key_allegations"]) == 2
    ), f"key_allegations should have 2 items, got {len(case_data['key_allegations'])}: {case_data['key_allegations']}"


@pytest.mark.django_db
def test_preservation_json_fields():
    """
    Preservation Test: JSON fields (versionInfo) should serialize correctly after fix

    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)

    This test captures the current serialization behavior for JSON fields.
    """
    # Create a case
    case = create_case_with_entities(
        title="JSON Fields Preservation Test",
        case_type=CaseType.CORRUPTION,
        description="Test case for JSON field preservation",
        key_allegations=["JSON test allegation"],
        state=CaseState.PUBLISHED,
    )

    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")

    assert response.status_code == 200
    case_data = response.data

    # Test JSON field preservation
    assert "versionInfo" in case_data, "Response should include 'versionInfo' field"
    # versionInfo can be dict, None, or empty dict depending on case state
    version_info = case_data["versionInfo"]
    assert isinstance(
        version_info, (dict, type(None))
    ), f"versionInfo should be dict or null, got {type(version_info)}: {version_info}"

    # Test other optional fields that might be JSON-like
    assert "notes" in case_data, "Response should include 'notes' field"
    notes = case_data["notes"]
    assert isinstance(
        notes, (str, type(None))
    ), f"notes should be string or null, got {type(notes)}: {notes}"


@pytest.mark.django_db
def test_preservation_optional_fields():
    """
    Preservation Test: Optional fields should maintain their presence/absence after fix

    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)

    This test captures the current behavior for optional fields.
    """
    # Create a case with minimal data (many optional fields will be empty/null)
    case = create_case_with_entities(
        title="Optional Fields Preservation Test",
        case_type=CaseType.PROMISES,
        description="Test case for optional field preservation",
        key_allegations=["Optional field test"],
        state=CaseState.PUBLISHED,
    )

    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")

    assert response.status_code == 200
    case_data = response.data

    # Test optional fields that should be present but may be empty/null
    optional_fields = [
        "short_description",
        "thumbnail_url",
        "banner_url",
        "case_start_date",
        "case_end_date",
        "notes",
    ]

    for field in optional_fields:
        assert field in case_data, f"Response should include optional field '{field}'"
        field_value = case_data[field]
        # Optional fields can be string, null, or empty string
        assert isinstance(
            field_value, (str, type(None))
        ), f"Optional field '{field}' should be string or null, got {type(field_value)}: {field_value}"


@pytest.mark.django_db
@settings(max_examples=5, deadline=800)
@given(case_data=complete_case_data())
def test_preservation_property_based_non_entity_fields(case_data):
    """
    Property-Based Preservation Test: Non-entity fields across various case configurations

    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)

    Property: For any case configuration, non-entity fields should serialize consistently
    and maintain their types and structures after the entity schema fix.

    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    # Create a case with the generated data
    case = create_case_with_entities(**case_data)
    case.state = CaseState.PUBLISHED
    case.save()

    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    assert response.status_code == 200

    case_response = response.data

    # Test preservation of core non-entity fields
    core_fields = {
        "id": int,
        "case_id": str,
        "title": str,
        "case_type": str,
        "state": str,
        "description": str,
        "key_allegations": list,
        "timeline": list,
        "evidence": list,
        "tags": list,
        "created_at": str,
        "updated_at": str,
    }

    for field_name, expected_type in core_fields.items():
        assert (
            field_name in case_response
        ), f"Response should include core field '{field_name}'"
        field_value = case_response[field_name]
        assert isinstance(
            field_value, expected_type
        ), f"Field '{field_name}' should be {expected_type.__name__}, got {type(field_value).__name__}: {field_value}"

    # Test preservation of optional fields (can be present and null/empty)
    optional_fields = [
        "short_description",
        "thumbnail_url",
        "banner_url",
        "case_start_date",
        "case_end_date",
        "notes",
        "versionInfo",
    ]

    for field_name in optional_fields:
        assert (
            field_name in case_response
        ), f"Response should include optional field '{field_name}'"
        # Optional fields can have various types or be null, but should be present in response

    # Verify that the response structure is consistent
    assert isinstance(
        case_response, dict
    ), f"Response should be dict, got {type(case_response)}"

    # Verify that array fields are actually arrays
    array_fields = ["key_allegations", "timeline", "evidence", "tags"]
    for field_name in array_fields:
        field_value = case_response[field_name]
        assert isinstance(
            field_value, list
        ), f"Array field '{field_name}' should be list, got {type(field_value)}: {field_value}"


@pytest.mark.django_db
def test_preservation_response_structure_consistency():
    """
    Preservation Test: Overall response structure should remain consistent after fix

    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)

    This test captures the overall response structure that should be preserved.
    """
    # Create a case
    case = create_case_with_entities(
        title="Response Structure Preservation Test",
        case_type=CaseType.CORRUPTION,
        description="Test case for response structure preservation",
        key_allegations=["Structure test allegation"],
        state=CaseState.PUBLISHED,
    )

    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")

    assert response.status_code == 200
    case_data = response.data

    # Test that response is a dictionary (not array or other type)
    assert isinstance(
        case_data, dict
    ), f"Response should be dict, got {type(case_data)}"

    # Test that response has a reasonable number of fields (not too few, not too many)
    field_count = len(case_data.keys())
    assert (
        field_count >= 15
    ), f"Response should have at least 15 fields, got {field_count}: {list(case_data.keys())}"
    assert (
        field_count <= 30
    ), f"Response should have at most 30 fields, got {field_count}: {list(case_data.keys())}"

    # Test that all field names are strings
    for field_name in case_data.keys():
        assert isinstance(
            field_name, str
        ), f"Field name should be string, got {type(field_name)}: {field_name}"

    # Test that response doesn't contain unexpected nested structures
    for field_name, field_value in case_data.items():
        # Fields should be basic types or simple arrays/dicts, not deeply nested
        if isinstance(field_value, dict):
            # Nested dicts should be simple (like versionInfo)
            assert (
                len(field_value) <= 10
            ), f"Nested dict '{field_name}' should be simple, got {len(field_value)} keys: {field_value}"
        elif isinstance(field_value, list):
            # Arrays should contain simple objects or primitives
            if len(field_value) > 0:
                first_item = field_value[0]
                if isinstance(first_item, dict):
                    # Array items that are dicts should be simple
                    assert (
                        len(first_item) <= 10
                    ), f"Array item in '{field_name}' should be simple dict, got {len(first_item)} keys: {first_item}"


@pytest.mark.django_db
def test_preservation_case_with_entities_non_entity_fields():
    """
    Preservation Test: Non-entity fields should be unaffected when entities are present

    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)

    This test ensures that the presence of entities doesn't affect non-entity field serialization.
    """
    # Create entities
    entity_person = create_entities_from_ids(["entity:person/preservation-test"])[0]

    # Create a case with entities
    case = create_case_with_entities(
        title="Preservation with Entities Test",
        case_type=CaseType.CORRUPTION,
        description="Test case for preservation when entities are present",
        key_allegations=["Preservation with entities allegation"],
        state=CaseState.PUBLISHED,
    )

    # Add entity relationship
    CaseEntityRelationship.objects.create(
        case=case,
        entity=entity_person,
        relationship_type=RelationshipType.ALLEGED,
        notes="Preservation test entity",
    )

    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")

    assert response.status_code == 200
    case_data = response.data

    # Test that non-entity fields are still properly serialized
    assert "title" in case_data, "Title should be present even when entities exist"
    assert (
        case_data["title"] == case.title
    ), f"Title should match case.title, got {case_data['title']}"

    assert (
        "description" in case_data
    ), "Description should be present even when entities exist"
    assert (
        case_data["description"] == case.description
    ), "Description should match case.description"

    assert (
        "key_allegations" in case_data
    ), "Key allegations should be present even when entities exist"
    assert (
        case_data["key_allegations"] == case.key_allegations
    ), "Key allegations should match case.key_allegations"

    assert (
        "case_type" in case_data
    ), "Case type should be present even when entities exist"
    assert (
        case_data["case_type"] == case.case_type.value
    ), "Case type should match case.case_type"

    assert "state" in case_data, "State should be present even when entities exist"
    assert case_data["state"] == case.state.value, "State should match case.state"

    # Verify that entity fields are also present (but we're not testing their content here)
    assert "entities" in case_data, "Entities field should be present"
    assert "locations" in case_data, "Locations field should be present"

    # The key point is that non-entity fields should be unaffected by entity presence
    # This establishes the baseline that must be preserved during the fix
