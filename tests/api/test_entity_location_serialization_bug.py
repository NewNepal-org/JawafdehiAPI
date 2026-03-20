"""
Bug Condition Exploration Test for Entity Location Serialization Fix

This test is designed to FAIL on unfixed code to demonstrate the bug exists.
The bug: API endpoints are missing legacy entity fields (alleged_entities, related_entities)
that are required for backward compatibility, and the SimplifiedEntitySerializer returns
relationship IDs instead of entity IDs.

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**DO NOT attempt to fix the test or the code when it fails.**

Feature: entity-location-serialization-fix
Property 1: Bug Condition - Missing Legacy Entity Fields and Wrong ID Mapping
Validates: Requirements 1.1, 1.2, 1.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient

from cases.models import CaseState, CaseType, CaseEntityRelationship, RelationshipType
from tests.conftest import create_case_with_entities, create_entities_from_ids
from tests.strategies import complete_case_data_with_timeline as complete_case_data


@pytest.mark.django_db
def test_bug_condition_missing_legacy_entity_fields():
    """
    Bug Condition Exploration: Missing legacy entity fields in API response
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    This test demonstrates that API responses are missing the legacy alleged_entities
    and related_entities fields that are required for backward compatibility.
    """
    # Create entities for the case using the unified relationship system
    entity_person = create_entities_from_ids(["entity:person/ram-bahadur-shrestha"])[0]
    entity_org = create_entities_from_ids(["entity:organization/nepal-government"])[0]
    
    # Create a case with complete data
    case = create_case_with_entities(
        title="Test Corruption Case",
        case_type=CaseType.CORRUPTION,
        description="Test case for missing legacy fields bug",
        key_allegations=["Misuse of public funds", "Nepotism in hiring"],
        state=CaseState.PUBLISHED
    )
    
    # Add entity relationships using the unified system
    CaseEntityRelationship.objects.create(
        case=case,
        entity=entity_person,
        relationship_type=RelationshipType.ALLEGED,
        notes="Primary accused person"
    )
    
    CaseEntityRelationship.objects.create(
        case=case,
        entity=entity_org,
        relationship_type=RelationshipType.RELATED,
        notes="Related organization"
    )
    
    # Make API request to case detail endpoint
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200, f"API should return 200 OK, got {response.status_code}"
    
    case_data = response.data
    
    # **BUG CONDITION**: These assertions will FAIL on unfixed code
    # The bug is that legacy fields are missing from the API response
    
    # Test that legacy fields are present (required for backward compatibility)
    assert "alleged_entities" in case_data, "Response should include alleged_entities field for backward compatibility"
    assert "related_entities" in case_data, "Response should include related_entities field for backward compatibility"
    
    # Verify legacy fields are arrays
    alleged_entities = case_data["alleged_entities"]
    related_entities = case_data["related_entities"]
    
    assert isinstance(alleged_entities, list), f"alleged_entities should be a list, but got {type(alleged_entities).__name__}: {alleged_entities}"
    assert isinstance(related_entities, list), f"related_entities should be a list, but got {type(related_entities).__name__}: {related_entities}"
    
    # Verify we have the expected entities
    assert len(alleged_entities) == 1, f"Should have 1 alleged entity, got {len(alleged_entities)}: {alleged_entities}"
    assert len(related_entities) == 1, f"Should have 1 related entity, got {len(related_entities)}: {related_entities}"
    
    # Verify entity structure in legacy fields
    alleged_entity = alleged_entities[0]
    assert isinstance(alleged_entity, dict), f"Alleged entity should be a dict, but got {type(alleged_entity).__name__}: {alleged_entity}"
    assert "id" in alleged_entity, f"Alleged entity should have 'id' field: {alleged_entity}"
    assert "nes_id" in alleged_entity, f"Alleged entity should have 'nes_id' field: {alleged_entity}"
    assert "display_name" in alleged_entity, f"Alleged entity should have 'display_name' field: {alleged_entity}"
    
    # **ADDITIONAL BUG**: The id field should be the entity ID, not the relationship ID
    assert alleged_entity["id"] == entity_person.id, f"Alleged entity id should be entity.id ({entity_person.id}), but got relationship.id ({alleged_entity['id']})"
    assert alleged_entity["nes_id"] == entity_person.nes_id, f"Alleged entity nes_id should match: expected {entity_person.nes_id}, got {alleged_entity['nes_id']}"


@pytest.mark.django_db
def test_bug_condition_wrong_entity_id_in_unified_fields():
    """
    Bug Condition Exploration: Wrong entity ID in unified fields
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    This test demonstrates that the unified entities and locations fields return
    relationship IDs instead of entity IDs in the 'id' field.
    """
    # Create entities
    entity_person = create_entities_from_ids(["entity:person/test-person"])[0]
    
    # Create a case
    case = create_case_with_entities(
        title="Test Case for ID Bug",
        case_type=CaseType.CORRUPTION,
        description="Test case for wrong ID bug",
        key_allegations=["Test allegation"],
        state=CaseState.PUBLISHED
    )
    
    # Add entity relationship
    relationship = CaseEntityRelationship.objects.create(
        case=case,
        entity=entity_person,
        relationship_type=RelationshipType.ALLEGED,
        notes="Test relationship"
    )
    
    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    # Test unified entities field
    assert "entities" in case_data, "Response should include entities field"
    entities = case_data["entities"]
    assert isinstance(entities, list), "entities should be a list"
    assert len(entities) == 1, "Should have exactly 1 entity"
    
    entity = entities[0]
    
    # **BUG CONDITION**: This will FAIL on unfixed code
    # The id field should be the entity ID, not the relationship ID
    assert entity["id"] == entity_person.id, f"Entity id should be entity.id ({entity_person.id}), but got relationship.id ({entity['id']})"
    assert entity["nes_id"] == entity_person.nes_id, f"Entity nes_id should match: expected {entity_person.nes_id}, got {entity['nes_id']}"


@pytest.mark.django_db
@settings(max_examples=5, deadline=800)
@given(case_data=complete_case_data())
def test_bug_condition_property_based_entities_serialization(case_data):
    """
    Property-Based Bug Condition Exploration: Entity serialization across various cases
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    Property: For any case with entity relationships, the API should return entities 
    and locations as arrays of objects, not as the string "string".
    
    **Validates: Requirements 1.1, 1.2, 1.3**
    """
    # Create a case with the generated data
    case = create_case_with_entities(**case_data)
    case.state = CaseState.PUBLISHED
    case.save()
    
    # Add at least one entity relationship using unified system
    entity = create_entities_from_ids(["entity:person/test-person"])[0]
    CaseEntityRelationship.objects.create(
        case=case,
        entity=entity,
        relationship_type=RelationshipType.ALLEGED,
        notes="Test relationship"
    )
    
    # Test both endpoints
    client = APIClient()
    
    # Test detail endpoint
    detail_response = client.get(f"/api/cases/{case.id}/")
    assert detail_response.status_code == 200
    
    detail_data = detail_response.data
    
    # **BUG CONDITION**: This will FAIL on unfixed code
    assert "entities" in detail_data, "Detail response should include entities field"
    assert isinstance(detail_data["entities"], list), f"entities should be list, got {type(detail_data['entities']).__name__}: {detail_data['entities']}"
    
    assert "locations" in detail_data, "Detail response should include locations field"
    assert isinstance(detail_data["locations"], list), f"locations should be list, got {type(detail_data['locations']).__name__}: {detail_data['locations']}"
    
    # Test list endpoint
    list_response = client.get("/api/cases/")
    assert list_response.status_code == 200
    
    results = list_response.data.get("results", [])
    our_case = next((c for c in results if c.get("case_id") == case.case_id), None)
    
    if our_case:  # Case might not appear in list if it doesn't meet publication criteria
        # **BUG CONDITION**: This will FAIL on unfixed code
        assert "entities" in our_case, "List response should include entities field"
        assert isinstance(our_case["entities"], list), f"entities should be list, got {type(our_case['entities']).__name__}: {our_case['entities']}"
        
        assert "locations" in our_case, "List response should include locations field"
        assert isinstance(our_case["locations"], list), f"locations should be list, got {type(our_case['locations']).__name__}: {our_case['locations']}"


@pytest.mark.django_db
def test_bug_condition_empty_entities_case():
    """
    Bug Condition Exploration: Case with no entities should return empty arrays
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    Even cases with no entity relationships should return empty arrays [],
    not the string "string".
    """
    # Create a case with no entity relationships
    case = create_case_with_entities(
        title="Case with No Entities",
        case_type=CaseType.CORRUPTION,
        description="Test case with no entity relationships",
        key_allegations=["General allegation"],
        state=CaseState.PUBLISHED
    )
    
    # Ensure no entity relationships exist
    assert case.entity_relationships.count() == 0, "Case should have no entity relationships"
    
    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    # **BUG CONDITION**: These will FAIL on unfixed code
    # Even empty cases should return empty arrays, not "string"
    
    assert "entities" in case_data, "Response should include entities field"
    entities = case_data["entities"]
    assert isinstance(entities, list), f"entities should be empty list, got {type(entities).__name__}: {entities}"
    assert len(entities) == 0, f"entities should be empty list, got: {entities}"
    
    assert "locations" in case_data, "Response should include locations field"
    locations = case_data["locations"]
    assert isinstance(locations, list), f"locations should be empty list, got {type(locations).__name__}: {locations}"
    assert len(locations) == 0, f"locations should be empty list, got: {locations}"


@pytest.mark.django_db
def test_bug_condition_mixed_entity_types():
    """
    Bug Condition Exploration: Case with mixed entity types (alleged, related, witness, etc.)
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    Tests that all relationship types are properly serialized as object arrays.
    """
    # Create entities of different types
    alleged_person = create_entities_from_ids(["entity:person/corrupt-official"])[0]
    related_org = create_entities_from_ids(["entity:organization/ministry-finance"])[0]
    witness_person = create_entities_from_ids(["entity:person/whistleblower"])[0]
    location = create_entities_from_ids(["entity:location/singha-durbar"])[0]
    
    # Create case
    case = create_case_with_entities(
        title="Complex Corruption Case",
        case_type=CaseType.CORRUPTION,
        description="Case with multiple entity relationship types",
        key_allegations=["Embezzlement", "Bribery"],
        state=CaseState.PUBLISHED
    )
    
    # Add different types of relationships
    CaseEntityRelationship.objects.create(
        case=case,
        entity=alleged_person,
        relationship_type=RelationshipType.ALLEGED,
        notes="Main accused"
    )
    
    CaseEntityRelationship.objects.create(
        case=case,
        entity=related_org,
        relationship_type=RelationshipType.RELATED,
        notes="Organization involved"
    )
    
    CaseEntityRelationship.objects.create(
        case=case,
        entity=witness_person,
        relationship_type=RelationshipType.WITNESS,
        notes="Key witness"
    )
    
    CaseEntityRelationship.objects.create(
        case=case,
        entity=location,
        relationship_type=RelationshipType.RELATED,
        notes="Location of incident"
    )
    
    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    # **BUG CONDITION**: These will FAIL on unfixed code
    
    # Test entities (non-location entities)
    assert "entities" in case_data, "Response should include entities field"
    entities = case_data["entities"]
    assert isinstance(entities, list), f"entities should be list, got {type(entities).__name__}: {entities}"
    assert len(entities) >= 3, f"Should have at least 3 non-location entities, got {len(entities)}: {entities}"
    
    # Verify entity types are properly serialized
    entity_types = [entity.get("type") for entity in entities if isinstance(entity, dict)]
    expected_types = ["alleged", "related", "witness"]
    for expected_type in expected_types:
        assert expected_type in entity_types, f"Should include entity with type '{expected_type}', got types: {entity_types}"
    
    # Test locations (location entities)
    assert "locations" in case_data, "Response should include locations field"
    locations = case_data["locations"]
    assert isinstance(locations, list), f"locations should be list, got {type(locations).__name__}: {locations}"
    
    # Location entities should be filtered into locations field
    if len(locations) > 0:
        for location in locations:
            assert isinstance(location, dict), f"Location should be dict, got {type(location).__name__}: {location}"
            assert location.get("nes_id", "").startswith("entity:location/"), f"Location should have location nes_id: {location}"