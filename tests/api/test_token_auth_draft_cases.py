"""
Tests for token-based authentication to access DRAFT cases.

Feature: Allow optional token-based authorization for GET /cases/<id> endpoint
"""

import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

from cases.models import CaseState, CaseType
from tests.conftest import create_case_with_entities

User = get_user_model()


@pytest.mark.django_db
class TestTokenAuthDraftCases:
    """Test token-based access to DRAFT cases."""

    def setup_method(self):
        """Set up test data for each test."""
        self.client = APIClient()

        # Create users with different roles
        self.admin_user = User.objects.create_user(
            username="admin", password="password"
        )
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.admin_token = Token.objects.create(user=self.admin_user)

        self.contributor_user = User.objects.create_user(
            username="contributor", password="password"
        )
        from django.contrib.auth.models import Group

        contributor_group, _ = Group.objects.get_or_create(name="Contributor")
        self.contributor_user.groups.add(contributor_group)
        self.contributor_token = Token.objects.create(user=self.contributor_user)

        self.other_contributor = User.objects.create_user(
            username="other_contributor", password="password"
        )
        self.other_contributor.groups.add(contributor_group)
        self.other_contributor_token = Token.objects.create(user=self.other_contributor)

    def test_draft_case_not_accessible_without_auth(self):
        """DRAFT case should return 404 for unauthenticated requests."""
        # Create a DRAFT case
        case = create_case_with_entities(
            title="Draft Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.DRAFT,
        )

        # Try to access without authentication
        response = self.client.get(f"/api/cases/{case.id}/")

        assert response.status_code == 404

    def test_draft_case_accessible_with_admin_token(self):
        """DRAFT case should be accessible to admin with token."""
        # Create a DRAFT case
        case = create_case_with_entities(
            title="Draft Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.DRAFT,
        )

        # Access with admin token
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        response = self.client.get(f"/api/cases/{case.id}/")

        assert response.status_code == 200
        assert response.data["case_id"] == case.case_id
        assert response.data["state"] == CaseState.DRAFT

    def test_draft_case_accessible_to_assigned_contributor(self):
        """DRAFT case should be accessible to assigned contributor with token."""
        # Create a DRAFT case
        case = create_case_with_entities(
            title="Draft Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.DRAFT,
        )

        # Assign contributor to the case
        case.contributors.add(self.contributor_user)

        # Access with contributor token
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.contributor_token.key}"
        )
        response = self.client.get(f"/api/cases/{case.id}/")

        assert response.status_code == 200
        assert response.data["case_id"] == case.case_id
        assert response.data["state"] == CaseState.DRAFT

    def test_draft_case_not_accessible_to_unassigned_contributor(self):
        """DRAFT case should NOT be accessible to unassigned contributor."""
        # Create a DRAFT case assigned to contributor_user
        case = create_case_with_entities(
            title="Draft Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.DRAFT,
        )
        case.contributors.add(self.contributor_user)

        # Try to access with other_contributor token (not assigned)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.other_contributor_token.key}"
        )
        response = self.client.get(f"/api/cases/{case.id}/")

        assert response.status_code == 404
        assert response.data["detail"] == "Not found."

    def test_published_case_accessible_without_auth(self):
        """PUBLISHED case should still be accessible without authentication."""
        # Create a PUBLISHED case
        case = create_case_with_entities(
            title="Published Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.PUBLISHED,
        )

        # Access without authentication
        response = self.client.get(f"/api/cases/{case.id}/")

        assert response.status_code == 200
        assert response.data["case_id"] == case.case_id
        assert response.data["state"] == CaseState.PUBLISHED

    def test_in_review_case_accessible_without_auth(self):
        """IN_REVIEW case should still be accessible without authentication."""
        # Create an IN_REVIEW case
        case = create_case_with_entities(
            title="In Review Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.IN_REVIEW,
        )

        # Access without authentication
        response = self.client.get(f"/api/cases/{case.id}/")

        assert response.status_code == 200
        assert response.data["case_id"] == case.case_id
        assert response.data["state"] == CaseState.IN_REVIEW

    def test_closed_case_not_accessible_without_auth(self):
        """CLOSED case should return 404 for unauthenticated requests."""
        # Create a CLOSED case
        case = create_case_with_entities(
            title="Closed Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.CLOSED,
        )

        # Try to access without authentication
        response = self.client.get(f"/api/cases/{case.id}/")

        assert response.status_code == 404

    def test_closed_case_accessible_with_admin_token(self):
        """CLOSED case should be accessible to admin with token."""
        # Create a CLOSED case
        case = create_case_with_entities(
            title="Closed Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.CLOSED,
        )

        # Access with admin token
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        response = self.client.get(f"/api/cases/{case.id}/")

        assert response.status_code == 200
        assert response.data["case_id"] == case.case_id
        assert response.data["state"] == CaseState.CLOSED

    def test_list_endpoint_still_only_shows_published(self):
        """List endpoint should still only show PUBLISHED cases regardless of auth."""
        # Create cases in different states
        draft_case = create_case_with_entities(
            title="Draft Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.DRAFT,
        )
        draft_case.contributors.add(self.contributor_user)

        published_case = create_case_with_entities(
            title="Published Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.PUBLISHED,
        )

        # Access list endpoint with contributor token
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.contributor_token.key}"
        )
        response = self.client.get("/api/cases/")

        assert response.status_code == 200
        case_ids = [c["case_id"] for c in response.data["results"]]

        # Only published case should appear
        assert published_case.case_id in case_ids
        assert draft_case.case_id not in case_ids
