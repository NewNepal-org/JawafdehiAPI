from tests.conftest import create_case_with_entities, create_entities_from_ids
"""
Tests for EXPOSE_CASES_IN_REVIEW feature flag.

Validates that the feature flag correctly controls visibility of IN_REVIEW cases.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from cases.models import Case, CaseState, CaseType, DocumentSource


User = get_user_model()


@pytest.mark.django_db
class TestExposeCasesInReviewFeatureFlag:
    """
    Tests for EXPOSE_CASES_IN_REVIEW feature flag behavior.
    
    These tests explicitly enable/disable the feature flag to verify
    its impact on API behavior.
    """
    
    def setup_method(self):
        """Set up test data for each test."""
        self.client = APIClient()
        
        # Create a published case
        self.published_case = create_case_with_entities(
            title="Published Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Published case description",
            state=CaseState.PUBLISHED,
            version=1
        )
        
        # Create an in-review case
        self.in_review_case = create_case_with_entities(
            title="In Review Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="In review case description",
            state=CaseState.IN_REVIEW,
            version=1
        )
        
        # Create a draft case
        self.draft_case = create_case_with_entities(
            title="Draft Case",
            alleged_entities=["entity:person/test"],
            case_type=CaseType.CORRUPTION,
            state=CaseState.DRAFT,
            version=1
        )
    
    def test_flag_disabled_hides_in_review_cases(self, settings):
        """
        When EXPOSE_CASES_IN_REVIEW=False, IN_REVIEW cases should not appear.
        """
        settings.EXPOSE_CASES_IN_REVIEW = False
        
        # List endpoint
        response = self.client.get('/api/cases/')
        assert response.status_code == 200
        
        case_ids = [case['case_id'] for case in response.data.get('results', [])]
        
        assert self.published_case.case_id in case_ids, \
            "Published case should appear"
        assert self.in_review_case.case_id not in case_ids, \
            "IN_REVIEW case should NOT appear when flag is disabled"
        assert self.draft_case.case_id not in case_ids, \
            "Draft case should never appear"
        
        # Detail endpoint - IN_REVIEW should return 404
        response = self.client.get(f'/api/cases/{self.in_review_case.id}/')
        assert response.status_code == 404, \
            "IN_REVIEW case should not be accessible when flag is disabled"
        
        # Published case should be accessible
        response = self.client.get(f'/api/cases/{self.published_case.id}/')
        assert response.status_code == 200
    
    def test_flag_enabled_shows_in_review_cases(self, settings):
        """
        When EXPOSE_CASES_IN_REVIEW=True, IN_REVIEW cases should appear.
        """
        settings.EXPOSE_CASES_IN_REVIEW = True
        
        # List endpoint
        response = self.client.get('/api/cases/')
        assert response.status_code == 200
        
        case_ids = [case['case_id'] for case in response.data.get('results', [])]
        
        assert self.published_case.case_id in case_ids, \
            "Published case should appear"
        assert self.in_review_case.case_id in case_ids, \
            "IN_REVIEW case should appear when flag is enabled"
        assert self.draft_case.case_id not in case_ids, \
            "Draft case should never appear"
        
        # Detail endpoint - IN_REVIEW should be accessible
        response = self.client.get(f'/api/cases/{self.in_review_case.id}/')
        assert response.status_code == 200, \
            "IN_REVIEW case should be accessible when flag is enabled"
        
        # Published case should still be accessible
        response = self.client.get(f'/api/cases/{self.published_case.id}/')
        assert response.status_code == 200
    
    def test_state_field_always_present(self, settings):
        """
        State field should always appear in response, regardless of flag value.
        """
        # Test with flag disabled
        settings.EXPOSE_CASES_IN_REVIEW = False
        
        response = self.client.get(f'/api/cases/{self.published_case.id}/')
        assert response.status_code == 200
        
        assert 'state' in response.data, \
            "State field should always appear"
        assert response.data['state'] == CaseState.PUBLISHED
        
        # Test with flag enabled
        settings.EXPOSE_CASES_IN_REVIEW = True
        
        # Check published case
        response = self.client.get(f'/api/cases/{self.published_case.id}/')
        assert response.status_code == 200
        
        assert 'state' in response.data, \
            "State field should always appear"
        assert response.data['state'] == CaseState.PUBLISHED
        
        # Check in-review case
        response = self.client.get(f'/api/cases/{self.in_review_case.id}/')
        assert response.status_code == 200
        
        assert 'state' in response.data, \
            "State field should always appear"
        assert response.data['state'] == CaseState.IN_REVIEW
    
    def test_flag_enabled_shows_in_review_sources(self, settings):
        """
        When EXPOSE_CASES_IN_REVIEW=True, sources from IN_REVIEW cases should appear.
        """
        # Create sources
        published_source = DocumentSource(
            title="Published Source",
            description="Source for published case"
        )
        published_source.save()
        
        in_review_source = DocumentSource(
            title="In Review Source",
            description="Source for in-review case"
        )
        in_review_source.save()
        
        # Add evidence to cases
        self.published_case.evidence = [{
            "source_id": published_source.source_id,
            "description": "Evidence from published case"
        }]
        self.published_case.save()
        
        self.in_review_case.evidence = [{
            "source_id": in_review_source.source_id,
            "description": "Evidence from in-review case"
        }]
        self.in_review_case.save()
        
        # Test with flag disabled
        settings.EXPOSE_CASES_IN_REVIEW = False
        response = self.client.get('/api/sources/')
        assert response.status_code == 200
        
        source_ids = [s['source_id'] for s in response.data.get('results', [])]
        assert published_source.source_id in source_ids
        assert in_review_source.source_id not in source_ids, \
            "IN_REVIEW source should NOT appear when flag is disabled"
        
        # Test with flag enabled
        settings.EXPOSE_CASES_IN_REVIEW = True
        response = self.client.get('/api/sources/')
        assert response.status_code == 200
        
        source_ids = [s['source_id'] for s in response.data.get('results', [])]
        assert published_source.source_id in source_ids
        assert in_review_source.source_id in source_ids, \
            "IN_REVIEW source should appear when flag is enabled"
    
    def test_flag_enabled_includes_in_review_in_audit_history(self, settings):
        """
        When EXPOSE_CASES_IN_REVIEW=True, audit history should include IN_REVIEW versions.
        """
        # Create version 1 (published)
        case_v1 = create_case_with_entities(
            title="Case v1",
            alleged_entities=["entity:person/test"],
            key_allegations=["Allegation v1"],
            case_type=CaseType.CORRUPTION,
            description="Version 1",
            state=CaseState.PUBLISHED,
            version=1,
            versionInfo={
                "version_number": 1,
                "action": "published",
                "datetime": "2024-01-15T10:00:00Z"
            }
        )
        
        case_id = case_v1.case_id
        
        # Create version 2 (in review)
        case_v2 = case_v1.create_draft()
        case_v2.title = "Case v2"
        case_v2.state = CaseState.IN_REVIEW
        case_v2.versionInfo = {
            "version_number": 2,
            "action": "submitted",
            "datetime": "2024-02-20T14:30:00Z"
        }
        case_v2.save()
        
        # Test with flag disabled - should only see v1
        settings.EXPOSE_CASES_IN_REVIEW = False
        response = self.client.get(f'/api/cases/{case_v1.id}/')
        assert response.status_code == 200
        
        audit_history = response.data.get('audit_history', [])
        assert len(audit_history) == 1, \
            "Should only include PUBLISHED version when flag is disabled"
        assert audit_history[0]['version_number'] == 1
        
        # Test with flag enabled - should see both v1 and v2
        settings.EXPOSE_CASES_IN_REVIEW = True
        
        # Access v2 (the IN_REVIEW version)
        response = self.client.get(f'/api/cases/{case_v2.id}/')
        assert response.status_code == 200
        
        audit_history = response.data.get('audit_history', [])
        assert len(audit_history) == 2, \
            "Should include both PUBLISHED and IN_REVIEW versions when flag is enabled"
        assert audit_history[0]['version_number'] == 2
        assert audit_history[1]['version_number'] == 1
    
    def test_draft_cases_never_appear_regardless_of_flag(self, settings):
        """
        Draft cases should never appear, regardless of feature flag setting.
        """
        # Test with flag disabled
        settings.EXPOSE_CASES_IN_REVIEW = False
        response = self.client.get('/api/cases/')
        case_ids = [case['case_id'] for case in response.data.get('results', [])]
        assert self.draft_case.case_id not in case_ids
        
        response = self.client.get(f'/api/cases/{self.draft_case.id}/')
        assert response.status_code == 404
        
        # Test with flag enabled
        settings.EXPOSE_CASES_IN_REVIEW = True
        response = self.client.get('/api/cases/')
        case_ids = [case['case_id'] for case in response.data.get('results', [])]
        assert self.draft_case.case_id not in case_ids
        
        response = self.client.get(f'/api/cases/{self.draft_case.id}/')
        assert response.status_code == 404
