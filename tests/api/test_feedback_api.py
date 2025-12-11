"""
Tests for the public Feedback API endpoint.
"""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from cases.models import Feedback, FeedbackType, FeedbackStatus


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestFeedbackSubmission:
    """Test suite for feedback submission."""
    
    def test_submit_minimal_feedback(self, api_client):
        """Test submitting feedback with only required fields."""
        data = {
            "feedbackType": "general",
            "subject": "Great platform",
            "description": "This platform is very helpful"
        }
        
        response = api_client.post('/api/feedback/', data, format='json')
        assert response.status_code == 201
        
        response_data = response.json()
        assert response_data['feedbackType'] == 'general'
        assert response_data['status'] == 'submitted'
        assert 'id' in response_data
        
        feedback = Feedback.objects.get(id=response_data['id'])
        assert feedback.feedback_type == FeedbackType.GENERAL
        assert feedback.status == FeedbackStatus.SUBMITTED
    
    def test_submit_feedback_with_contact_info(self, api_client):
        """Test submitting feedback with contact information."""
        data = {
            "feedbackType": "bug",
            "subject": "Search not working",
            "description": "Detailed bug description",
            "contactInfo": {
                "name": "राम बहादुर",
                "contactMethods": [
                    {"type": "email", "value": "ram@example.com"}
                ]
            }
        }
        
        response = api_client.post('/api/feedback/', data, format='json')
        assert response.status_code == 201
        
        feedback = Feedback.objects.get(id=response.json()['id'])
        assert feedback.contact_info['name'] == 'राम बहादुर'
    
    def test_submit_all_feedback_types(self, api_client):
        """Test submitting all feedback types."""
        types = ["bug", "feature", "usability", "content", "general"]
        
        for feedback_type in types:
            data = {
                "feedbackType": feedback_type,
                "subject": f"Test {feedback_type}",
                "description": "Test description"
            }
            
            response = api_client.post('/api/feedback/', data, format='json')
            assert response.status_code == 201


@pytest.mark.django_db
class TestFeedbackValidation:
    """Test suite for feedback validation."""
    
    def test_missing_required_fields(self, api_client):
        """Test that required fields are validated."""
        # Missing feedbackType
        response = api_client.post('/api/feedback/', {
            "subject": "Test",
            "description": "Test"
        }, format='json')
        assert response.status_code == 400
        
        # Missing subject
        response = api_client.post('/api/feedback/', {
            "feedbackType": "bug",
            "description": "Test"
        }, format='json')
        assert response.status_code == 400
        
        # Missing description
        response = api_client.post('/api/feedback/', {
            "feedbackType": "bug",
            "subject": "Test"
        }, format='json')
        assert response.status_code == 400
    
    def test_invalid_feedback_type(self, api_client):
        """Test that invalid feedback type is rejected."""
        data = {
            "feedbackType": "invalid_type",
            "subject": "Test",
            "description": "Test description"
        }
        
        response = api_client.post('/api/feedback/', data, format='json')
        assert response.status_code == 400


@pytest.mark.django_db
class TestFeedbackRateLimiting:
    """Test suite for feedback rate limiting."""
    
    def test_rate_limit_allows_five_submissions(self, api_client):
        """Test that 5 submissions within an hour are allowed."""
        data = {
            "feedbackType": "general",
            "subject": "Test",
            "description": "Test description"
        }
        
        for i in range(5):
            response = api_client.post(
                '/api/feedback/',
                data,
                format='json',
                REMOTE_ADDR='192.168.1.100'
            )
            assert response.status_code == 201
        
        assert Feedback.objects.count() == 5
    
    def test_rate_limit_blocks_sixth_submission(self, api_client):
        """Test that 6th submission within an hour is blocked."""
        data = {
            "feedbackType": "general",
            "subject": "Test",
            "description": "Test description"
        }
        
        for _ in range(5):
            api_client.post(
                '/api/feedback/',
                data,
                format='json',
                REMOTE_ADDR='192.168.1.100'
            )
        
        response = api_client.post(
            '/api/feedback/',
            data,
            format='json',
            REMOTE_ADDR='192.168.1.100'
        )
        assert response.status_code == 429
        assert Feedback.objects.count() == 5
    
    def test_rate_limit_per_ip_address(self, api_client):
        """Test that rate limit is per IP address."""
        data = {
            "feedbackType": "general",
            "subject": "Test",
            "description": "Test description"
        }
        
        # 5 from first IP
        for _ in range(5):
            api_client.post(
                '/api/feedback/',
                data,
                format='json',
                REMOTE_ADDR='192.168.1.100'
            )
        
        # 6th from same IP blocked
        response = api_client.post(
            '/api/feedback/',
            data,
            format='json',
            REMOTE_ADDR='192.168.1.100'
        )
        assert response.status_code == 429
        
        # Different IP succeeds
        response = api_client.post(
            '/api/feedback/',
            data,
            format='json',
            REMOTE_ADDR='192.168.1.200'
        )
        assert response.status_code == 201
