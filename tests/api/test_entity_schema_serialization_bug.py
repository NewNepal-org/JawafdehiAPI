"""
Bug Condition Exploration Test for Entity Schema Serialization Fix

This test is designed to FAIL on unfixed code to demonstrate the schema discrepancy bug exists.
The bug: API responses return complex nested structures with separate "alleged_entities", 
"related_entities", and "locations" arrays containing internal relationship metadata, 
instead of the documented unified "entities" array with simple structure.

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**DO NOT attempt to fix the test or the code when it fails.**

Feature: entity-schema-serialization-fix
Property 1: Bug Condition - Schema Discrepancy Detection
Validates: Requirements 2.1, 2.2, 2.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient

from cases.models import CaseState, CaseType, CaseEntityRelationship, RelationshipType
from tests.conftest import create_case_with_entities, create_entities_from_ids
from tests.strategies import complete_case_data_with_timeline as complete_case_data


@pytest.mark.django_db
def test_bug_condition_unified_entities_schema_compliance():
    """
    Bug Condition Exploration: API should return unified entities array with simple structure
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    This test demonstrates that API responses return complex nested structures instead
    of the documented unified "entities" array format with simple fields.
    """
    # Create entities for testing
    entity_person = create_entities_from_ids(["entity:person/ram-bahadur-thapa"])[0]
    entity_org = create_entities_from_ids(["entity:organization/nepal-telecom"])[0]
    entity_location = create_entities_from_ids(["entity:location/district/kathmandu"])[0]
    
    # Create a case with complete data
    case = create_case_with_entities(
        title="Schema Compliance Test Case",
        case_type=CaseType.CORRUPTION,
        description="Test case for schema discrepancy bug",
        key_allegations=["Misuse of public funds", "Illegal contract awards"],
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
    
    CaseEntityRelationship.objects.create(
        case=case,
        entity=entity_location,
        relationship_type=RelationshipType.WITNESS,
        notes="Location of incident"
    )
    
    # Make API request to case detail endpoint
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200, f"API should return 200 OK, got {response.status_code}"
    
    case_data = response.data
    
    # **BUG CONDITION**: These assertions will FAIL on unfixed code
    # The bug is that the API returns complex nested structures instead of unified format
    
    # DEBUG: Print the actual response structure
    print(f"\n=== DEBUG: Case with Entities Response Structure ===")
    entity_fields = ["entities", "locations", "alleged_entities", "related_entities"]
    for field in entity_fields:
        if field in case_data:
            field_data = case_data[field]
            print(f"{field}: {type(field_data).__name__} with {len(field_data)} items")
            if len(field_data) > 0:
                print(f"  Sample: {field_data[0]}")
        else:
            print(f"{field}: NOT PRESENT")
    print("=" * 60)
    
    # Test 1: Unified entities array should be the PRIMARY entity field
    assert "entities" in case_data, "Response should include unified 'entities' array as primary entity field"
    entities = case_data["entities"]
    assert isinstance(entities, list), f"entities should be a list, but got {type(entities).__name__}: {entities}"
    
    # Test 2: Entities should contain simple objects with documented schema fields only
    assert len(entities) >= 2, f"Should have at least 2 entities (person + org), got {len(entities)}: {entities}"
    
    for entity in entities:
        assert isinstance(entity, dict), f"Entity should be a dict, but got {type(entity).__name__}: {entity}"
        
        # Required simple fields from documented schema
        required_fields = {"id", "nes_id", "display_name", "type", "notes"}
        entity_fields = set(entity.keys())
        
        # Verify all required fields are present
        missing_fields = required_fields - entity_fields
        assert not missing_fields, f"Entity missing required fields {missing_fields}: {entity}"
        
        # Verify no complex relationship metadata is included
        forbidden_fields = {"alleged_cases", "related_cases"}
        forbidden_present = forbidden_fields & entity_fields
        assert not forbidden_present, f"Entity should not include internal relationship metadata {forbidden_present}: {entity}"
        
        # Verify field types and values
        assert isinstance(entity["id"], int), f"Entity id should be integer, got {type(entity['id'])}: {entity['id']}"
        assert isinstance(entity["nes_id"], (str, type(None))), f"Entity nes_id should be string or null, got {type(entity['nes_id'])}: {entity['nes_id']}"
        assert isinstance(entity["display_name"], (str, type(None))), f"Entity display_name should be string or null, got {type(entity['display_name'])}: {entity['display_name']}"
        assert isinstance(entity["type"], str), f"Entity type should be string, got {type(entity['type'])}: {entity['type']}"
        assert isinstance(entity["notes"], (str, type(None))), f"Entity notes should be string or null, got {type(entity['notes'])}: {entity['notes']}"
    
    # Test 3: Response should NOT have complex nested arrays as primary fields
    # The BUG is that BOTH unified and legacy fields are present, creating schema confusion
    complex_fields = {"alleged_entities", "related_entities"}
    for field in complex_fields:
        if field in case_data:
            print(f"🐛 BUG DETECTED: Legacy field '{field}' is present alongside unified format")
            field_data = case_data[field]
            # The bug is that we have BOTH formats, not that legacy fields have complex metadata
            # According to the user's description, they want ONLY the unified format
            assert False, f"Schema discrepancy: Both unified 'entities' and legacy '{field}' are present. API should use unified format only."


@pytest.mark.django_db
def test_bug_condition_entity_id_mapping_correctness():
    """
    Bug Condition Exploration: Entity ID should map to entity.id, not relationship.id
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    This test demonstrates that the SimplifiedEntitySerializer should return the actual
    entity ID (entity.id) in the 'id' field, not the relationship ID.
    """
    # Create multiple entities first to ensure different IDs
    dummy_entities = create_entities_from_ids([
        "entity:person/dummy-1", 
        "entity:person/dummy-2"
    ])
    
    # Create a specific entity to test ID mapping
    entity_person = create_entities_from_ids(["entity:person/test-id-mapping"])[0]
    
    # Create multiple cases first to ensure different relationship IDs
    dummy_case = create_case_with_entities(
        title="Dummy Case",
        case_type=CaseType.PROMISES,
        description="Dummy case to offset IDs",
        key_allegations=["Dummy allegation"],
        state=CaseState.PUBLISHED
    )
    
    # Create a case
    case = create_case_with_entities(
        title="ID Mapping Test Case",
        case_type=CaseType.CORRUPTION,
        description="Test case for entity ID mapping",
        key_allegations=["Test allegation for ID mapping"],
        state=CaseState.PUBLISHED
    )
    
    # Add some dummy relationships first to offset relationship IDs
    for dummy_entity in dummy_entities:
        CaseEntityRelationship.objects.create(
            case=dummy_case,
            entity=dummy_entity,
            relationship_type=RelationshipType.RELATED,
            notes="Dummy relationship"
        )
    
    # Add entity relationship and capture the relationship ID
    relationship = CaseEntityRelationship.objects.create(
        case=case,
        entity=entity_person,
        relationship_type=RelationshipType.ALLEGED,
        notes="Test relationship for ID mapping"
    )
    
    # Make API request
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    # Find our entity in the unified entities array
    entities = case_data.get("entities", [])
    assert len(entities) >= 1, f"Should have at least 1 entity, got {len(entities)}: {entities}"
    
    # Find the entity that matches our test entity
    test_entity = None
    for entity in entities:
        if isinstance(entity, dict) and entity.get("nes_id") == entity_person.nes_id:
            test_entity = entity
            break
    
    assert test_entity is not None, f"Could not find test entity with nes_id {entity_person.nes_id} in entities: {entities}"
    
    # **BUG CONDITION**: This will FAIL on unfixed code
    # The id field should be the entity ID, not the relationship ID
    assert test_entity["id"] == entity_person.id, f"Entity id should be entity.id ({entity_person.id}), but got {test_entity['id']}"
    
    # Additional validation: verify the serializer is using the correct source
    # The SimplifiedEntitySerializer should map 'id' to 'entity.id'
    print(f"DEBUG: Entity ID: {entity_person.id}, Relationship ID: {relationship.id}, Serialized ID: {test_entity['id']}")
    
    # The key test is that we get the entity ID, regardless of whether it matches relationship ID
    assert isinstance(test_entity["id"], int), f"Entity id should be integer, got {type(test_entity['id'])}"
    assert test_entity["id"] > 0, f"Entity id should be positive, got {test_entity['id']}"


@pytest.mark.django_db
def test_bug_condition_no_internal_relationship_metadata():
    """
    Bug Condition Exploration: Response should exclude internal relationship metadata
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    This test demonstrates that entity objects should not include internal relationship
    metadata like "alleged_cases" and "related_cases" arrays.
    """
    # Create multiple entities and cases to create relationship metadata
    entity1 = create_entities_from_ids(["entity:person/metadata-test-1"])[0]
    entity2 = create_entities_from_ids(["entity:person/metadata-test-2"])[0]
    
    # Create multiple cases to generate relationship metadata
    case1 = create_case_with_entities(
        title="Metadata Test Case 1",
        case_type=CaseType.CORRUPTION,
        description="First case for metadata test",
        key_allegations=["Test allegation 1"],
        state=CaseState.PUBLISHED
    )
    
    case2 = create_case_with_entities(
        title="Metadata Test Case 2", 
        case_type=CaseType.PROMISES,
        description="Second case for metadata test",
        key_allegations=["Test allegation 2"],
        state=CaseState.PUBLISHED
    )
    
    # Create relationships that would generate metadata
    CaseEntityRelationship.objects.create(
        case=case1,
        entity=entity1,
        relationship_type=RelationshipType.ALLEGED,
        notes="Entity1 alleged in case1"
    )
    
    CaseEntityRelationship.objects.create(
        case=case2,
        entity=entity1,
        relationship_type=RelationshipType.RELATED,
        notes="Entity1 related to case2"
    )
    
    CaseEntityRelationship.objects.create(
        case=case1,
        entity=entity2,
        relationship_type=RelationshipType.WITNESS,
        notes="Entity2 witness in case1"
    )
    
    # Test case1 response
    client = APIClient()
    response = client.get(f"/api/cases/{case1.id}/")
    
    assert response.status_code == 200
    case_data = response.data
    
    entities = case_data.get("entities", [])
    assert len(entities) >= 2, f"Should have at least 2 entities, got {len(entities)}: {entities}"
    
    # **BUG CONDITION**: These will FAIL on unfixed code
    # Entities should not contain internal relationship metadata
    for entity in entities:
        if isinstance(entity, dict):
            # Check that internal relationship metadata is not present
            forbidden_metadata = {"alleged_cases", "related_cases"}
            entity_fields = set(entity.keys())
            metadata_present = forbidden_metadata & entity_fields
            
            assert not metadata_present, f"Entity should not contain internal relationship metadata {metadata_present}: {entity}"
            
            # Verify only the documented simple fields are present
            expected_fields = {"id", "nes_id", "display_name", "type", "notes"}
            unexpected_fields = entity_fields - expected_fields
            
            assert not unexpected_fields, f"Entity contains unexpected fields {unexpected_fields}, should only have {expected_fields}: {entity}"


@pytest.mark.django_db
@settings(max_examples=3, deadline=800)
@given(case_data=complete_case_data())
def test_bug_condition_property_based_unified_schema(case_data):
    """
    Property-Based Bug Condition Exploration: Unified schema compliance across various cases
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    Property: For any case with entity relationships, the API should return a unified
    "entities" array with simple structure matching the documented schema.
    
    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    # Create a case with the generated data
    case = create_case_with_entities(**case_data)
    case.state = CaseState.PUBLISHED
    case.save()
    
    # Add at least one entity relationship using unified system
    entity = create_entities_from_ids(["entity:person/property-test"])[0]
    CaseEntityRelationship.objects.create(
        case=case,
        entity=entity,
        relationship_type=RelationshipType.ALLEGED,
        notes="Property-based test relationship"
    )
    
    # Test the API response
    client = APIClient()
    response = client.get(f"/api/cases/{case.id}/")
    assert response.status_code == 200
    
    case_data = response.data
    
    # **BUG CONDITION**: These will FAIL on unfixed code
    
    # Test unified entities array is present and properly structured
    assert "entities" in case_data, "Response should include unified 'entities' array"
    entities = case_data["entities"]
    assert isinstance(entities, list), f"entities should be list, got {type(entities).__name__}: {entities}"
    assert len(entities) >= 1, f"Should have at least 1 entity, got {len(entities)}: {entities}"
    
    # Test each entity has the correct simple structure
    for entity in entities:
        assert isinstance(entity, dict), f"Entity should be dict, got {type(entity).__name__}: {entity}"
        
        # Required fields from documented schema
        required_fields = {"id", "nes_id", "display_name", "type", "notes"}
        entity_fields = set(entity.keys())
        
        missing_fields = required_fields - entity_fields
        assert not missing_fields, f"Entity missing required fields {missing_fields}: {entity}"
        
        # No internal relationship metadata
        forbidden_fields = {"alleged_cases", "related_cases"}
        forbidden_present = forbidden_fields & entity_fields
        assert not forbidden_present, f"Entity should not include metadata {forbidden_present}: {entity}"


@pytest.mark.django_db
def test_bug_condition_empty_case_unified_schema():
    """
    Bug Condition Exploration: Empty case should return empty unified entities array
    
    **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    
    Even cases with no entity relationships should return an empty unified entities array,
    following the documented schema structure.
    """
    # Create a case with no entity relationships
    case = create_case_with_entities(
        title="Empty Case Schema Test",
        case_type=CaseType.CORRUPTION,
        description="Test case with no entity relationships for schema compliance",
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
    # Even empty cases should follow the unified schema structure
    
    # DEBUG: Print the actual response structure
    print(f"\n=== DEBUG: Empty Case Response Structure ===")
    entity_fields = ["entities", "locations", "alleged_entities", "related_entities"]
    for field in entity_fields:
        if field in case_data:
            print(f"{field}: {type(case_data[field]).__name__} = {case_data[field]}")
        else:
            print(f"{field}: NOT PRESENT")
    print("=" * 50)
    
    assert "entities" in case_data, "Response should include unified 'entities' field"
    entities = case_data["entities"]
    assert isinstance(entities, list), f"entities should be empty list, got {type(entities).__name__}: {entities}"
    assert len(entities) == 0, f"entities should be empty list, got: {entities}"
    
    # The response should follow the documented schema structure
    # Complex nested arrays should not be the primary entity representation
    if "alleged_entities" in case_data:
        # If legacy fields exist, they should also be properly structured
        alleged = case_data["alleged_entities"]
        assert isinstance(alleged, list), f"alleged_entities should be list if present, got {type(alleged).__name__}: {alleged}"
        assert len(alleged) == 0, f"alleged_entities should be empty list, got: {alleged}"