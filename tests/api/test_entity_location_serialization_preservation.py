"""
Preservation Property Tests for Entity Location Serialization Fix

These tests capture the CURRENT behavior of non-entity fields on UNFIXED code.
They must PASS on unfixed code to establish the baseline behavior that must be preserved.

**IMPORTANT**: Follow observation-first methodology
- Observe behavior on UNFIXED code for non-entity fields
- Write property-based tests capturing observed behavior patterns
- Run tests on UNFIXED code
- **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)

Feature: entity-location-serialization-fix
Property 2: Preservation - Non-Entity Field Serialization Unchanged
Validates: Requirements 3.1, 3.2, 3.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient
from datetime import datetime, timezone

from cases.models import CaseState, CaseType, CaseEntityRelationship, RelationshipType
from tests.conftest import create_case_with_entities, create_entities_from_ids
from tests.strategies import complete_case_data_with_timeline as complete_case_data


@pytest.mark.django_db
def test_preservation_non_entity_fields_basic():
    """
    Preservation Test: Non-entity fields serialize correctly on unfixed code
    
    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)
    
    This test captures the current serialization behavior for all non-entity fields
    that must remain unchanged after the fix.
    """
    # Create a case with comprehensive non-entity field data
    case = create_case_with_entities(
        title="Preservation Test Case",
        case_type=CaseType.CORRUPTION,
        description="This is a detailed description of the corruption case",
        key_allegations=["Misuse of public funds", "Nepotism in hiring", "Bribery"],
        tags=["corruption", "government", "finance"],
        timeline=[
            {
                "date": "2024-01-15",
                "title": "Initial Report",
                "description": "First report of misconduct received"
            },
            {
                "date": "2024-02-01", 
                "title": "Investigation Started",
                "description": "Official investigation launched"
            }
        ],
        evidence=[
            {
                "source_id": "source:20240115:abc123",
                "description": "Bank records showing suspicious transactions"
            },
            {
                "source_id": "source:20240201:def456", 
                "description": "Email correspondence between officials"
            }
        ],
        notes="Internal notes about the case progress",
        state=CaseState.PUBLISHED
    )
    
    # Set versionInfo to test JSON field serialization
    case.versionInfo = {
        "action": "published",
        "datetime": "2024-01-15T10:30:00Z",
        "version": 1
    }
    case.save()
    
    # Make API request to case detail endpoint
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200, f"API should return 200 OK, got {response.status_code}"
    
    case_data = response.data
    
    # Test that all non-entity fields are present and correctly serialized
    # These assertions capture the CURRENT behavior that must be preserved
    
    # Core identification fields
    assert "id" in case_data, "Response should include id field"
    assert case_data["id"] == case.id, f"id should match: expected {case.id}, got {case_data['id']}"
    
    assert "case_id" in case_data, "Response should include case_id field"
    assert case_data["case_id"] == case.case_id, f"case_id should match: expected {case.case_id}, got {case_data['case_id']}"
    
    # Core content fields
    assert "title" in case_data, "Response should include title field"
    assert case_data["title"] == case.title, f"title should match: expected {case.title}, got {case_data['title']}"
    
    assert "description" in case_data, "Response should include description field"
    assert case_data["description"] == case.description, f"description should match: expected {case.description}, got {case_data['description']}"
    
    assert "case_type" in case_data, "Response should include case_type field"
    assert case_data["case_type"] == case.case_type, f"case_type should match: expected {case.case_type}, got {case_data['case_type']}"
    
    assert "state" in case_data, "Response should include state field"
    assert case_data["state"] == case.state, f"state should match: expected {case.state}, got {case_data['state']}"
    
    # List fields
    assert "key_allegations" in case_data, "Response should include key_allegations field"
    assert isinstance(case_data["key_allegations"], list), f"key_allegations should be list, got {type(case_data['key_allegations'])}"
    assert case_data["key_allegations"] == case.key_allegations, f"key_allegations should match: expected {case.key_allegations}, got {case_data['key_allegations']}"
    
    assert "tags" in case_data, "Response should include tags field"
    assert isinstance(case_data["tags"], list), f"tags should be list, got {type(case_data['tags'])}"
    assert case_data["tags"] == case.tags, f"tags should match: expected {case.tags}, got {case_data['tags']}"
    
    # Complex structured fields
    assert "timeline" in case_data, "Response should include timeline field"
    assert isinstance(case_data["timeline"], list), f"timeline should be list, got {type(case_data['timeline'])}"
    assert case_data["timeline"] == case.timeline, f"timeline should match: expected {case.timeline}, got {case_data['timeline']}"
    
    assert "evidence" in case_data, "Response should include evidence field"
    assert isinstance(case_data["evidence"], list), f"evidence should be list, got {type(case_data['evidence'])}"
    assert case_data["evidence"] == case.evidence, f"evidence should match: expected {case.evidence}, got {case_data['evidence']}"
    
    # Metadata fields
    assert "notes" in case_data, "Response should include notes field"
    assert case_data["notes"] == case.notes, f"notes should match: expected {case.notes}, got {case_data['notes']}"
    
    assert "versionInfo" in case_data, "Response should include versionInfo field"
    assert isinstance(case_data["versionInfo"], dict), f"versionInfo should be dict, got {type(case_data['versionInfo'])}"
    assert case_data["versionInfo"] == case.versionInfo, f"versionInfo should match: expected {case.versionInfo}, got {case_data['versionInfo']}"
    
    # Timestamp fields
    assert "created_at" in case_data, "Response should include created_at field"
    assert "updated_at" in case_data, "Response should include updated_at field"
    
    # Optional fields that may be present
    if hasattr(case, 'short_description') and case.short_description:
        assert "short_description" in case_data, "Response should include short_description field if present"
        assert case_data["short_description"] == case.short_description
    
    if hasattr(case, 'thumbnail_url') and case.thumbnail_url:
        assert "thumbnail_url" in case_data, "Response should include thumbnail_url field if present"
        assert case_data["thumbnail_url"] == case.thumbnail_url
    
    if hasattr(case, 'banner_url') and case.banner_url:
        assert "banner_url" in case_data, "Response should include banner_url field if present"
        assert case_data["banner_url"] == case.banner_url
    
    # Date fields
    if hasattr(case, 'case_start_date') and case.case_start_date:
        assert "case_start_date" in case_data, "Response should include case_start_date field if present"
        assert case_data["case_start_date"] == case.case_start_date.isoformat()
    
    if hasattr(case, 'case_end_date') and case.case_end_date:
        assert "case_end_date" in case_data, "Response should include case_end_date field if present"
        assert case_data["case_end_date"] == case.case_end_date.isoformat()


@pytest.mark.django_db
def test_preservation_empty_list_fields():
    """
    Preservation Test: Empty list fields serialize correctly
    
    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)
    
    Tests that empty list fields (tags, key_allegations, timeline, evidence) 
    serialize as empty arrays, not null or other values.
    """
    # Create a case with minimal data and empty list fields
    case = create_case_with_entities(
        title="Minimal Case",
        case_type=CaseType.CORRUPTION,
        description="Minimal case for testing empty fields",
        key_allegations=[],  # Empty list
        tags=[],  # Empty list
        timeline=[],  # Empty list
        evidence=[],  # Empty list
        state=CaseState.PUBLISHED
    )
    
    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    # Test that empty list fields serialize as empty arrays
    assert "key_allegations" in case_data, "Response should include key_allegations field"
    assert case_data["key_allegations"] == [], f"key_allegations should be empty list, got {case_data['key_allegations']}"
    
    assert "tags" in case_data, "Response should include tags field"
    assert case_data["tags"] == [], f"tags should be empty list, got {case_data['tags']}"
    
    assert "timeline" in case_data, "Response should include timeline field"
    assert case_data["timeline"] == [], f"timeline should be empty list, got {case_data['timeline']}"
    
    assert "evidence" in case_data, "Response should include evidence field"
    assert case_data["evidence"] == [], f"evidence should be empty list, got {case_data['evidence']}"


@pytest.mark.django_db
def test_preservation_null_optional_fields():
    """
    Preservation Test: Null optional fields serialize correctly
    
    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)
    
    Tests that optional fields that are null/empty serialize correctly.
    """
    # Create a case with minimal required fields only
    case = create_case_with_entities(
        title="Case with Null Fields",
        case_type=CaseType.CORRUPTION,
        description="Case for testing null field serialization",
        key_allegations=["Basic allegation"],
        state=CaseState.PUBLISHED
        # Deliberately omit optional fields
    )
    
    # Ensure optional fields are null/empty
    case.short_description = ""
    case.thumbnail_url = ""
    case.banner_url = ""
    case.case_start_date = None
    case.case_end_date = None
    case.notes = ""
    case.save()
    
    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    # Test that optional fields are handled correctly when empty/null
    # The exact behavior (null vs empty string vs omitted) should be preserved
    
    if "short_description" in case_data:
        assert case_data["short_description"] == case.short_description
    
    if "thumbnail_url" in case_data:
        assert case_data["thumbnail_url"] == case.thumbnail_url
    
    if "banner_url" in case_data:
        assert case_data["banner_url"] == case.banner_url
    
    if "case_start_date" in case_data:
        assert case_data["case_start_date"] is None
    
    if "case_end_date" in case_data:
        assert case_data["case_end_date"] is None
    
    # Notes field should be present (it's in the serializer fields)
    assert "notes" in case_data, "Response should include notes field"
    assert case_data["notes"] == case.notes


@pytest.mark.django_db
@settings(max_examples=10, deadline=800)
@given(case_data=complete_case_data())
def test_preservation_property_based_non_entity_fields(case_data):
    """
    Property-Based Preservation Test: Non-entity fields across various cases
    
    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)
    
    Property: For any case data, all non-entity fields should serialize identically
    to their model values, regardless of the entity serialization bug.
    
    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    # Create a case with the generated data
    case = create_case_with_entities(**case_data)
    case.state = CaseState.PUBLISHED
    case.save()
    
    # Test both detail and list endpoints
    client = APIClient()
    
    # Test detail endpoint
    detail_response = client.get(f"/api/cases/{case.id}/")
    assert detail_response.status_code == 200
    
    detail_data = detail_response.data
    
    # Test that core non-entity fields are preserved
    assert detail_data["title"] == case.title, f"title should match: expected {case.title}, got {detail_data['title']}"
    assert detail_data["description"] == case.description, f"description should match: expected {case.description}, got {detail_data['description']}"
    assert detail_data["case_type"] == case.case_type, f"case_type should match: expected {case.case_type}, got {detail_data['case_type']}"
    assert detail_data["state"] == case.state, f"state should match: expected {case.state}, got {detail_data['state']}"
    assert detail_data["case_id"] == case.case_id, f"case_id should match: expected {case.case_id}, got {detail_data['case_id']}"
    
    # Test list fields
    assert detail_data["key_allegations"] == case.key_allegations, f"key_allegations should match: expected {case.key_allegations}, got {detail_data['key_allegations']}"
    
    if case.tags:
        assert detail_data["tags"] == case.tags, f"tags should match: expected {case.tags}, got {detail_data['tags']}"
    
    if case.timeline:
        assert detail_data["timeline"] == case.timeline, f"timeline should match: expected {case.timeline}, got {detail_data['timeline']}"
    
    # Test list endpoint (if case appears in results)
    list_response = client.get("/api/cases/")
    assert list_response.status_code == 200
    
    results = list_response.data.get("results", [])
    our_case = next((c for c in results if c.get("case_id") == case.case_id), None)
    
    if our_case:  # Case might not appear in list if it doesn't meet publication criteria
        # Test that the same non-entity fields are preserved in list view
        assert our_case["title"] == case.title, f"List view title should match: expected {case.title}, got {our_case['title']}"
        assert our_case["case_type"] == case.case_type, f"List view case_type should match: expected {case.case_type}, got {our_case['case_type']}"
        assert our_case["state"] == case.state, f"List view state should match: expected {case.state}, got {our_case['state']}"
        assert our_case["case_id"] == case.case_id, f"List view case_id should match: expected {case.case_id}, got {our_case['case_id']}"


@pytest.mark.django_db
def test_preservation_version_info_json_field():
    """
    Preservation Test: versionInfo JSON field serializes correctly
    
    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)
    
    Tests that the versionInfo JSON field maintains its structure and content.
    """
    # Create a case with complex versionInfo
    case = create_case_with_entities(
        title="Version Info Test Case",
        case_type=CaseType.CORRUPTION,
        description="Testing versionInfo JSON field serialization",
        key_allegations=["Test allegation"],
        state=CaseState.PUBLISHED
    )
    
    # Set complex versionInfo data
    version_info = {
        "action": "published",
        "datetime": "2024-01-15T10:30:00Z",
        "version": 2,
        "changes": [
            {"field": "title", "old": "Old Title", "new": "New Title"},
            {"field": "description", "old": "Old desc", "new": "New desc"}
        ],
        "metadata": {
            "user_id": 123,
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0"
        }
    }
    case.versionInfo = version_info
    case.save()
    
    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    # Test that versionInfo is preserved exactly
    assert "versionInfo" in case_data, "Response should include versionInfo field"
    assert isinstance(case_data["versionInfo"], dict), f"versionInfo should be dict, got {type(case_data['versionInfo'])}"
    assert case_data["versionInfo"] == version_info, f"versionInfo should match exactly: expected {version_info}, got {case_data['versionInfo']}"
    
    # Test nested structure preservation
    assert case_data["versionInfo"]["action"] == "published"
    assert case_data["versionInfo"]["version"] == 2
    assert len(case_data["versionInfo"]["changes"]) == 2
    assert case_data["versionInfo"]["metadata"]["user_id"] == 123


@pytest.mark.django_db
def test_preservation_timestamp_fields():
    """
    Preservation Test: Timestamp fields serialize correctly
    
    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)
    
    Tests that created_at and updated_at timestamp fields maintain their format.
    """
    # Create a case
    case = create_case_with_entities(
        title="Timestamp Test Case",
        case_type=CaseType.CORRUPTION,
        description="Testing timestamp field serialization",
        key_allegations=["Test allegation"],
        state=CaseState.PUBLISHED
    )
    
    # Store original timestamps
    original_created_at = case.created_at
    original_updated_at = case.updated_at
    
    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    # Test timestamp field presence and format
    assert "created_at" in case_data, "Response should include created_at field"
    assert "updated_at" in case_data, "Response should include updated_at field"
    
    # Test that timestamps are strings (ISO format)
    assert isinstance(case_data["created_at"], str), f"created_at should be string, got {type(case_data['created_at'])}"
    assert isinstance(case_data["updated_at"], str), f"updated_at should be string, got {type(case_data['updated_at'])}"
    
    # Test that timestamps can be parsed back to datetime
    from datetime import datetime
    try:
        parsed_created = datetime.fromisoformat(case_data["created_at"].replace('Z', '+00:00'))
        parsed_updated = datetime.fromisoformat(case_data["updated_at"].replace('Z', '+00:00'))
        
        # Timestamps should be close to original (within a few seconds due to serialization)
        assert abs((parsed_created - original_created_at.replace(tzinfo=timezone.utc)).total_seconds()) < 5
        assert abs((parsed_updated - original_updated_at.replace(tzinfo=timezone.utc)).total_seconds()) < 5
        
    except ValueError as e:
        pytest.fail(f"Timestamp format should be parseable: {e}")


@pytest.mark.django_db
def test_preservation_case_list_endpoint():
    """
    Preservation Test: Case list endpoint preserves non-entity fields
    
    **EXPECTED OUTCOME**: Test PASSES (confirms baseline behavior to preserve)
    
    Tests that the list endpoint (/api/cases/) preserves the same non-entity
    field behavior as the detail endpoint.
    """
    # Create multiple cases to test list behavior
    cases = []
    for i in range(3):
        case = create_case_with_entities(
            title=f"List Test Case {i+1}",
            case_type=CaseType.CORRUPTION,
            description=f"Description for case {i+1}",
            key_allegations=[f"Allegation {i+1}A", f"Allegation {i+1}B"],
            tags=[f"tag{i+1}", "common-tag"],
            state=CaseState.PUBLISHED
        )
        cases.append(case)
    
    # Make API request to list endpoint
    client = APIClient()
    response = client.get("/api/cases/")
    
    assert response.status_code == 200
    response_data = response.data
    
    # Test pagination structure
    assert "results" in response_data, "List response should have results field"
    results = response_data["results"]
    assert isinstance(results, list), f"results should be list, got {type(results)}"
    
    # Test that our cases appear in results
    case_ids = [case.case_id for case in cases]
    result_case_ids = [result.get("case_id") for result in results]
    
    for case_id in case_ids:
        assert case_id in result_case_ids, f"Case {case_id} should appear in list results"
    
    # Test that each case in results has proper non-entity field structure
    for result in results:
        if result.get("case_id") in case_ids:
            # Find the corresponding case
            original_case = next(case for case in cases if case.case_id == result["case_id"])
            
            # Test core fields are preserved
            assert result["title"] == original_case.title
            assert result["case_type"] == original_case.case_type
            assert result["state"] == original_case.state
            assert result["case_id"] == original_case.case_id
            
            # Test list fields are preserved
            assert result["key_allegations"] == original_case.key_allegations
            assert result["tags"] == original_case.tags
            
            # Test that required fields are present
            required_fields = ["id", "case_id", "title", "case_type", "state", "created_at", "updated_at"]
            for field in required_fields:
                assert field in result, f"List result should include {field} field"