"""
End-to-End tests for public API workflows.

Feature: accountability-platform-core
Tests complete user workflows through the public API
Validates: Requirements 6.1, 6.2, 6.3, 8.1, 8.3
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from cases.models import Case, CaseState, CaseType, DocumentSource


User = get_user_model()


@pytest.mark.django_db
class TestPublicAPIWorkflows:
    """
    End-to-end tests for public API user workflows.
    
    These tests simulate complete user journeys through the API,
    testing the integration of multiple endpoints and features.
    """
    
    def setup_method(self):
        """Set up test data for each test."""
        self.client = APIClient()
        
        # Create test cases with different states and types
        self.published_corruption_case = Case.objects.create(
            title="Corruption Case - Land Encroachment",
            alleged_entities=["entity:person/test-official"],
            related_entities=["entity:organization/government/test-ministry"],
            locations=["entity:location/district/kathmandu"],
            key_allegations=[
                "Illegally acquired public land",
                "Failed to disclose assets"
            ],
            case_type=CaseType.CORRUPTION,
            description="A detailed description of the corruption case involving land encroachment.",
            tags=["land-encroachment", "public-land"],
            timeline=[
                {
                    "date": "2024-01-15",
                    "title": "Initial complaint filed",
                    "description": "Citizens filed complaint with authorities"
                },
                {
                    "date": "2024-02-20",
                    "title": "Investigation started",
                    "description": "Official investigation commenced"
                }
            ],
            state=CaseState.PUBLISHED,
            version=1
        )
        
        # Create a source for the corruption case
        self.corruption_source = DocumentSource(
            title="Land Registry Document",
            description="Official land registry showing illegal transfer",
            related_entity_ids=["entity:person/test-official"]
        )
        self.corruption_source.save()
        
        # Add evidence to the case
        self.published_corruption_case.evidence = [
            {
                "source_id": self.corruption_source.source_id,
                "description": "This document proves the illegal land transfer"
            }
        ]
        self.published_corruption_case.save()
        
        # Create another published case with different type
        self.published_promises_case = Case.objects.create(
            title="Broken Promise - Infrastructure Project",
            alleged_entities=["entity:person/test-politician"],
            key_allegations=["Failed to deliver promised infrastructure"],
            case_type=CaseType.PROMISES,
            description="Election promise to build hospital was not fulfilled.",
            tags=["infrastructure", "healthcare"],
            state=CaseState.PUBLISHED,
            version=1
        )
        
        # Create a draft case (should not be visible)
        self.draft_case = Case.objects.create(
            title="Draft Case - Should Not Appear",
            alleged_entities=["entity:person/test-person"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="This is a draft case",
            state=CaseState.DRAFT,
            version=1
        )
        
        # Create a closed case (should not be visible)
        self.closed_case = Case.objects.create(
            title="Closed Case - Should Not Appear",
            alleged_entities=["entity:person/test-person"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="This is a closed case",
            state=CaseState.CLOSED,
            version=1
        )
    
    def test_browse_filter_search_view_workflow(self):
        """
        E2E Test: Complete user workflow from browsing to viewing details.
        
        Workflow:
        1. Browse all cases (list endpoint)
        2. Filter by case type
        3. Search for specific term
        4. View detailed case information
        
        Validates: Requirements 6.1, 6.2, 6.3, 8.1
        """
        # Step 1: Browse all published cases
        response = self.client.get('/api/cases/')
        assert response.status_code == 200, "Browse endpoint should return 200"
        
        results = response.data.get('results', [])
        assert len(results) == 2, "Should return 2 published cases (not draft or closed)"
        
        # Verify only published cases appear
        case_titles = [case['title'] for case in results]
        assert "Corruption Case - Land Encroachment" in case_titles
        assert "Broken Promise - Infrastructure Project" in case_titles
        assert "Draft Case - Should Not Appear" not in case_titles
        assert "Closed Case - Should Not Appear" not in case_titles
        
        # Step 2: Filter by case type (CORRUPTION)
        response = self.client.get('/api/cases/?case_type=CORRUPTION')
        assert response.status_code == 200, "Filter endpoint should return 200"
        
        results = response.data.get('results', [])
        assert len(results) == 1, "Should return 1 corruption case"
        assert results[0]['case_type'] == CaseType.CORRUPTION
        assert results[0]['title'] == "Corruption Case - Land Encroachment"
        
        # Step 3: Search for specific term
        response = self.client.get('/api/cases/?search=land')
        assert response.status_code == 200, "Search endpoint should return 200"
        
        results = response.data.get('results', [])
        assert len(results) >= 1, "Should find at least 1 case with 'land' in content"
        
        # Find the corruption case in results
        corruption_case_result = next(
            (case for case in results if 'Land Encroachment' in case['title']),
            None
        )
        assert corruption_case_result is not None, "Should find the land encroachment case"
        
        # Step 4: View detailed case information
        case_id = corruption_case_result['id']
        response = self.client.get(f'/api/cases/{case_id}/')
        assert response.status_code == 200, "Detail endpoint should return 200"
        
        case_detail = response.data
        
        # Verify complete data is present
        assert case_detail['title'] == "Corruption Case - Land Encroachment"
        assert case_detail['description'] is not None
        assert len(case_detail['key_allegations']) == 2
        assert len(case_detail['timeline']) == 2
        assert len(case_detail['evidence']) == 1
        assert len(case_detail['tags']) == 2
        
        # Verify evidence includes source information
        evidence = case_detail['evidence'][0]
        assert 'source_id' in evidence
        assert 'description' in evidence
        assert evidence['source_id'] == self.corruption_source.source_id
    
    def test_only_published_cases_accessible(self):
        """
        E2E Test: Verify that only published cases are accessible through the API.
        
        Tests:
        1. List endpoint only shows published cases
        2. Draft cases are not accessible via detail endpoint
        3. Closed cases are not accessible via detail endpoint
        4. In Review cases are not accessible
        
        Validates: Requirements 6.1, 8.3
        """
        # Test 1: List endpoint only shows published cases
        response = self.client.get('/api/cases/')
        assert response.status_code == 200
        
        results = response.data.get('results', [])
        case_ids = [case['case_id'] for case in results]
        
        assert self.published_corruption_case.case_id in case_ids
        assert self.published_promises_case.case_id in case_ids
        assert self.draft_case.case_id not in case_ids
        assert self.closed_case.case_id not in case_ids
        
        # Test 2: Draft cases return 404 when accessed directly
        response = self.client.get(f'/api/cases/{self.draft_case.id}/')
        assert response.status_code == 404, \
            "Draft cases should not be accessible via detail endpoint"
        
        # Test 3: Closed cases return 404 when accessed directly
        response = self.client.get(f'/api/cases/{self.closed_case.id}/')
        assert response.status_code == 404, \
            "Closed cases should not be accessible via detail endpoint"
        
        # Test 4: Create an IN_REVIEW case and verify it's not accessible
        in_review_case = Case.objects.create(
            title="In Review Case - Should Not Appear",
            alleged_entities=["entity:person/test-person"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="This is an in-review case",
            state=CaseState.IN_REVIEW,
            version=1
        )
        
        response = self.client.get(f'/api/cases/{in_review_case.id}/')
        assert response.status_code == 404, \
            "In Review cases should not be accessible via detail endpoint"
        
        # Verify it doesn't appear in list
        response = self.client.get('/api/cases/')
        case_ids = [case['case_id'] for case in response.data.get('results', [])]
        assert in_review_case.case_id not in case_ids, \
            "In Review cases should not appear in list endpoint"
    
    def test_audit_history_retrieval(self):
        """
        E2E Test: Verify audit history is included when retrieving case details.
        
        Workflow:
        1. Create a published case (version 1)
        2. Create a draft from it and publish (version 2)
        3. Retrieve the case via API
        4. Verify audit history includes both versions
        
        Validates: Requirements 6.3, 7.1, 7.2
        """
        # Step 1: Create initial published case
        case_v1 = Case.objects.create(
            title="Case with Version History",
            alleged_entities=["entity:person/test-official"],
            key_allegations=["Initial allegation"],
            case_type=CaseType.CORRUPTION,
            description="Initial version of the case",
            state=CaseState.PUBLISHED,
            version=1,
            versionInfo={
                "version_number": 1,
                "user_id": "user123",
                "change_summary": "Initial publication",
                "datetime": "2024-01-15T10:00:00Z"
            }
        )
        
        case_id = case_v1.case_id
        
        # Step 2: Create a draft and publish it (version 2)
        case_v2 = case_v1.create_draft()
        case_v2.title = "Case with Version History - Updated"
        case_v2.key_allegations = ["Initial allegation", "Additional allegation"]
        case_v2.versionInfo = {
            "version_number": 2,
            "user_id": "user456",
            "change_summary": "Added new allegation",
            "datetime": "2024-02-20T14:30:00Z"
        }
        case_v2.state = CaseState.PUBLISHED
        case_v2.save()
        
        # Step 3: Retrieve the case via API (should get v2)
        response = self.client.get(f'/api/cases/{case_v2.id}/')
        assert response.status_code == 200
        
        case_detail = response.data
        
        # Verify we got version 2
        assert case_detail['title'] == "Case with Version History - Updated"
        assert len(case_detail['key_allegations']) == 2
        
        # Step 4: Verify audit history is included
        assert 'audit_history' in case_detail, \
            "Detail endpoint should include audit_history"
        
        audit_history = case_detail['audit_history']
        assert len(audit_history) == 2, \
            "Audit history should include both published versions"
        
        # Verify audit history is in reverse chronological order (newest first)
        assert audit_history[0]['version_number'] == 2, \
            "First entry should be version 2 (newest)"
        assert audit_history[1]['version_number'] == 1, \
            "Second entry should be version 1"
        
        # Verify audit history includes required fields
        for entry in audit_history:
            assert 'version_number' in entry
            assert 'user_id' in entry
            assert 'change_summary' in entry
            assert 'datetime' in entry
        
        # Verify specific audit details
        assert audit_history[0]['change_summary'] == "Added new allegation"
        assert audit_history[1]['change_summary'] == "Initial publication"
    
    def test_filter_by_tags_workflow(self):
        """
        E2E Test: Filter cases by tags and verify results.
        
        Workflow:
        1. Browse all cases
        2. Filter by specific tag
        3. Verify only cases with that tag are returned
        
        Validates: Requirements 6.2, 8.1
        """
        # Step 1: Browse all cases
        response = self.client.get('/api/cases/')
        assert response.status_code == 200
        initial_count = len(response.data.get('results', []))
        assert initial_count == 2, "Should have 2 published cases"
        
        # Step 2: Filter by tag "land-encroachment"
        response = self.client.get('/api/cases/?tags=land-encroachment')
        assert response.status_code == 200
        
        results = response.data.get('results', [])
        assert len(results) == 1, "Should return 1 case with 'land-encroachment' tag"
        
        # Step 3: Verify the correct case is returned
        case = results[0]
        assert case['title'] == "Corruption Case - Land Encroachment"
        assert 'land-encroachment' in case['tags']
        
        # Test filtering by another tag
        response = self.client.get('/api/cases/?tags=infrastructure')
        assert response.status_code == 200
        
        results = response.data.get('results', [])
        assert len(results) == 1, "Should return 1 case with 'infrastructure' tag"
        assert results[0]['title'] == "Broken Promise - Infrastructure Project"
    
    def test_search_across_multiple_fields(self):
        """
        E2E Test: Search functionality across title, description, and allegations.
        
        Workflow:
        1. Search for term in title
        2. Search for term in description
        3. Search for term in key allegations
        4. Verify all searches return correct results
        
        Validates: Requirements 6.2, 8.1
        """
        # Test 1: Search for term in title
        response = self.client.get('/api/cases/?search=Corruption')
        assert response.status_code == 200
        
        results = response.data.get('results', [])
        assert len(results) >= 1, "Should find cases with 'Corruption' in title"
        
        titles = [case['title'] for case in results]
        assert any('Corruption' in title for title in titles)
        
        # Test 2: Search for term in description
        response = self.client.get('/api/cases/?search=hospital')
        assert response.status_code == 200
        
        results = response.data.get('results', [])
        assert len(results) >= 1, "Should find cases with 'hospital' in description"
        
        # Verify the promises case is found
        found_promises_case = any(
            case['title'] == "Broken Promise - Infrastructure Project"
            for case in results
        )
        assert found_promises_case, "Should find the infrastructure case"
        
        # Test 3: Search for term in key allegations
        response = self.client.get('/api/cases/?search=assets')
        assert response.status_code == 200
        
        results = response.data.get('results', [])
        assert len(results) >= 1, "Should find cases with 'assets' in allegations"
        
        # Verify the corruption case is found
        found_corruption_case = any(
            case['title'] == "Corruption Case - Land Encroachment"
            for case in results
        )
        assert found_corruption_case, "Should find the corruption case"
    
    def test_document_source_visibility_workflow(self):
        """
        E2E Test: Verify document sources are only visible for published cases.
        
        Workflow:
        1. List all sources
        2. Verify only sources from published cases appear
        3. Retrieve specific source
        4. Verify source details are complete
        
        Validates: Requirements 4.1, 6.3
        """
        # Create a source referenced by the draft case (should not be visible)
        draft_source = DocumentSource(
            title="Draft Source - Should Not Appear",
            description="Source for draft case"
        )
        draft_source.save()
        
        # Add evidence to draft case referencing this source
        self.draft_case.evidence = [{
            "source_id": draft_source.source_id,
            "description": "Evidence from draft case"
        }]
        self.draft_case.save()
        
        # Step 1: List all sources
        response = self.client.get('/api/sources/')
        assert response.status_code == 200
        
        results = response.data.get('results', [])
        source_ids = [source['source_id'] for source in results]
        
        # Step 2: Verify only sources from published cases appear
        assert self.corruption_source.source_id in source_ids, \
            "Source from published case should appear"
        assert draft_source.source_id not in source_ids, \
            "Source from draft case should NOT appear"
        
        # Step 3: Retrieve specific source
        response = self.client.get(f'/api/sources/{self.corruption_source.id}/')
        assert response.status_code == 200
        
        # Step 4: Verify source details are complete
        source_detail = response.data
        assert source_detail['title'] == "Land Registry Document"
        assert source_detail['description'] is not None
        assert 'related_entity_ids' in source_detail
        assert len(source_detail['related_entity_ids']) > 0
        
        # Verify draft source is not accessible directly
        response = self.client.get(f'/api/sources/{draft_source.id}/')
        assert response.status_code == 404, \
            "Source from draft case should not be accessible"
    
    def test_highest_version_only_in_list(self):
        """
        E2E Test: Verify only the highest version of each case appears in list.
        
        Workflow:
        1. Create case version 1 (published)
        2. Create case version 2 (published)
        3. List all cases
        4. Verify only version 2 appears
        
        Validates: Requirements 6.1, 8.3
        """
        # Step 1: Create version 1
        case_v1 = Case.objects.create(
            title="Multi-Version Case v1",
            alleged_entities=["entity:person/test"],
            key_allegations=["Allegation v1"],
            case_type=CaseType.CORRUPTION,
            description="Version 1",
            state=CaseState.PUBLISHED,
            version=1
        )
        
        case_id = case_v1.case_id
        
        # Step 2: Create version 2
        case_v2 = case_v1.create_draft()
        case_v2.title = "Multi-Version Case v2"
        case_v2.description = "Version 2"
        case_v2.state = CaseState.PUBLISHED
        case_v2.save()
        
        # Step 3: List all cases
        response = self.client.get('/api/cases/')
        assert response.status_code == 200
        
        results = response.data.get('results', [])
        
        # Step 4: Verify only version 2 appears
        matching_cases = [
            case for case in results
            if case['case_id'] == case_id
        ]
        
        assert len(matching_cases) == 1, \
            "Should only return one version per case_id"
        
        returned_case = matching_cases[0]
        assert returned_case['title'] == "Multi-Version Case v2", \
            "Should return the highest version (v2)"
        assert returned_case['description'] == "Version 2"
    
    def test_pagination_workflow(self):
        """
        E2E Test: Verify pagination works correctly.
        
        Workflow:
        1. Create multiple published cases
        2. Request first page
        3. Verify pagination metadata
        4. Request next page if available
        
        Validates: Requirements 6.1, 8.1
        """
        # Create additional cases to test pagination
        for i in range(5):
            Case.objects.create(
                title=f"Pagination Test Case {i}",
                alleged_entities=["entity:person/test"],
                key_allegations=["Test allegation"],
                case_type=CaseType.CORRUPTION,
                description=f"Test case {i}",
                state=CaseState.PUBLISHED,
                version=1
            )
        
        # Request first page
        response = self.client.get('/api/cases/')
        assert response.status_code == 200
        
        # Verify pagination metadata exists
        assert 'count' in response.data, "Response should include total count"
        assert 'results' in response.data, "Response should include results"
        
        # Verify we have results
        results = response.data.get('results', [])
        assert len(results) > 0, "Should have at least some results"
        
        # Total count should be at least 7 (2 original + 5 new)
        total_count = response.data.get('count', 0)
        assert total_count >= 7, f"Should have at least 7 cases, got {total_count}"
