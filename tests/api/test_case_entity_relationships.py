"""
Integration tests for unified case entity relationship endpoints.

Tests the new /api/cases/{id}/entities/ endpoints that replace the legacy
alleged_entities and related_entities M2M relationships.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from cases.models import Case, CaseState, JawafEntity, CaseEntityRelationship, RelationshipType
from tests.conftest import create_user_with_role

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    return APIClient()


@pytest.fixture
def test_user():
    """Create a test user with contributor role."""
    return create_user_with_role("testuser", "test@example.com", "Contributor")


@pytest.fixture
def test_case(test_user):
    """Create a published test case."""
    case = Case.objects.create(
        case_id="test-case-001",
        title="Test Case",
        description="Test description",
        case_type="CORRUPTION",
        state=CaseState.PUBLISHED,
    )
    case.contributors.add(test_user)
    return case


@pytest.fixture
def test_entity():
    """Create a test entity."""
    return JawafEntity.objects.create(
        nes_id="entity:person/ram-bahadur-thapa",
        display_name="Ram Bahadur Thapa",
    )


@pytest.fixture
def another_entity():
    """Create another test entity."""
    return JawafEntity.objects.create(
        nes_id="entity:organization/ministry-of-finance",
        display_name="Ministry of Finance",
    )


class TestGetCaseEntities:
    """Tests for GET /api/cases/{id}/entities/"""

    def test_get_entities_returns_correct_shape(self, api_client, test_case, test_entity, another_entity):
        """Test that GET returns the correct response structure."""
        # Create relationships
        CaseEntityRelationship.objects.create(
            case=test_case,
            entity=test_entity,
            relationship_type=RelationshipType.ALLEGED,
            notes="Primary accused",
        )
        CaseEntityRelationship.objects.create(
            case=test_case,
            entity=another_entity,
            relationship_type=RelationshipType.RELATED,
            notes="Related organization",
        )

        response = api_client.get(f"/api/cases/{test_case.id}/entities/")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "relationships" in data
        assert "counts" in data

        # Check relationships array
        assert len(data["relationships"]) == 2
        relationship = data["relationships"][0]
        assert "id" in relationship
        assert "entity" in relationship
        assert "relationship_type" in relationship
        assert "notes" in relationship
        assert "created_at" in relationship

        # Check entity is an ID (not nested object)
        assert isinstance(relationship["entity"], int)

        # Check counts structure
        counts = data["counts"]
        assert "alleged" in counts
        assert "related" in counts
        assert "witness" in counts
        assert "opposition" in counts
        assert "victim" in counts
        assert "total" in counts
        assert counts["alleged"] == 1
        assert counts["related"] == 1
        assert counts["total"] == 2

    def test_get_entities_filters_by_relationship_type(self, api_client, test_case, test_entity, another_entity):
        """Test filtering by relationship_type parameter."""
        # Create relationships
        CaseEntityRelationship.objects.create(
            case=test_case,
            entity=test_entity,
            relationship_type=RelationshipType.ALLEGED,
        )
        CaseEntityRelationship.objects.create(
            case=test_case,
            entity=another_entity,
            relationship_type=RelationshipType.WITNESS,
        )

        # Filter for alleged only
        response = api_client.get(f"/api/cases/{test_case.id}/entities/?relationship_type=alleged")

        assert response.status_code == 200
        data = response.json()
        assert len(data["relationships"]) == 1
        assert data["relationships"][0]["relationship_type"] == "alleged"

        # Counts should still show all relationships
        assert data["counts"]["total"] == 2


class TestAddCaseEntity:
    """Tests for POST /api/cases/{id}/entities/"""

    def test_post_requires_authentication(self, api_client, test_case, test_entity):
        """Test that POST returns 401 without authentication."""
        response = api_client.post(
            f"/api/cases/{test_case.id}/entities/",
            {
                "entity": test_entity.id,
                "relationship_type": "alleged",
            },
            format="json",
        )

        assert response.status_code == 401

    def test_post_creates_relationship(self, api_client, test_case, test_entity, test_user):
        """Test that authenticated POST creates a relationship."""
        api_client.force_authenticate(user=test_user)

        response = api_client.post(
            f"/api/cases/{test_case.id}/entities/",
            {
                "entity": test_entity.id,
                "relationship_type": "alleged",
                "notes": "Test notes",
            },
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["entity"] == test_entity.id
        assert data["relationship_type"] == "alleged"
        assert data["notes"] == "Test notes"

        # Verify relationship was created in database
        assert CaseEntityRelationship.objects.filter(
            case=test_case,
            entity=test_entity,
            relationship_type=RelationshipType.ALLEGED,
        ).exists()

    def test_post_with_invalid_relationship_type_returns_400(self, api_client, test_case, test_entity, test_user):
        """Test that POST with invalid relationship_type returns 400."""
        api_client.force_authenticate(user=test_user)

        response = api_client.post(
            f"/api/cases/{test_case.id}/entities/",
            {
                "entity": test_entity.id,
                "relationship_type": "invalid_type",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_post_duplicate_relationship_returns_409(self, api_client, test_case, test_entity, test_user):
        """Test that duplicate relationship returns 409."""
        api_client.force_authenticate(user=test_user)

        # Create initial relationship
        api_client.post(
            f"/api/cases/{test_case.id}/entities/",
            {
                "entity": test_entity.id,
                "relationship_type": "alleged",
            },
            format="json",
        )

        # Try to create duplicate
        response = api_client.post(
            f"/api/cases/{test_case.id}/entities/",
            {
                "entity": test_entity.id,
                "relationship_type": "alleged",
            },
            format="json",
        )

        assert response.status_code == 409
        data = response.json()
        assert "duplicate_relationship" in data.get("error_code", "")


class TestDeleteCaseEntityRelationship:
    """Tests for DELETE /api/cases/{id}/entities/{relationship_id}/"""

    def test_delete_returns_204(self, api_client, test_case, test_entity, test_user):
        """Test that DELETE returns 204 on success."""
        api_client.force_authenticate(user=test_user)

        # Create relationship
        relationship = CaseEntityRelationship.objects.create(
            case=test_case,
            entity=test_entity,
            relationship_type=RelationshipType.ALLEGED,
        )

        response = api_client.delete(f"/api/cases/{test_case.id}/entities/{relationship.id}/")

        assert response.status_code == 204

        # Verify relationship was deleted
        assert not CaseEntityRelationship.objects.filter(id=relationship.id).exists()

    def test_delete_missing_relationship_returns_404(self, api_client, test_case, test_user):
        """Test that DELETE returns 404 for non-existent relationship."""
        api_client.force_authenticate(user=test_user)

        response = api_client.delete(f"/api/cases/{test_case.id}/entities/99999/")

        assert response.status_code == 404

    def test_delete_requires_authentication(self, api_client, test_case, test_entity):
        """Test that DELETE requires authentication."""
        # Create relationship
        relationship = CaseEntityRelationship.objects.create(
            case=test_case,
            entity=test_entity,
            relationship_type=RelationshipType.ALLEGED,
        )

        response = api_client.delete(f"/api/cases/{test_case.id}/entities/{relationship.id}/")

        assert response.status_code == 401
