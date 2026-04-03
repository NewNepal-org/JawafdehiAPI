"""
Tests for slug field behavior in caseworker API.

Tests slug validation, immutability, and error handling.
"""

import pytest
from django.contrib.auth import get_user_model

from cases.models import Case, CaseState, CaseType, JawafEntity, RelationshipType, CaseEntityRelationship

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = User.objects.create_user(
        username="admin_slug",
        email="admin_slug@example.com",
        password="testpass123",
    )
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def entity(db):
    """Create a test entity."""
    return JawafEntity.objects.create(
        nes_id="entity:person/test-person",
        display_name="Test Person",
    )


@pytest.mark.django_db
class TestCaseworkerSlugCreate:
    """Test slug field in case creation."""

    def test_create_case_with_valid_slug(self, client, admin_user):
        """Creating a case with valid slug should succeed."""
        client.force_login(admin_user)

        response = client.post(
            "/api/caseworker/cases/",
            data={
                "case_type": CaseType.CORRUPTION,
                "title": "Test Case",
                "slug": "test-case-slug",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        case = Case.objects.get(case_id=response.json()["case_id"])
        assert case.slug == "test-case-slug"

    def test_create_case_with_invalid_slug(self, client, admin_user):
        """Creating a case with invalid slug should fail with 400."""
        client.force_login(admin_user)

        response = client.post(
            "/api/caseworker/cases/",
            data={
                "case_type": CaseType.CORRUPTION,
                "title": "Test Case",
                "slug": "123-invalid",  # Starts with number
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "slug" in response.json()

    def test_create_case_without_slug(self, client, admin_user):
        """Creating a case without slug should succeed."""
        client.force_login(admin_user)

        response = client.post(
            "/api/caseworker/cases/",
            data={
                "case_type": CaseType.CORRUPTION,
                "title": "Test Case",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        case = Case.objects.get(case_id=response.json()["case_id"])
        assert case.slug is None or case.slug == ""


@pytest.mark.django_db
class TestCaseworkerSlugPatch:
    """Test slug immutability in PATCH operations."""

    def test_patch_cannot_change_slug(self, client, admin_user, entity):
        """Attempting to change slug via PATCH should return 400."""
        client.force_login(admin_user)

        # Create case with slug
        case = Case.objects.create(
            case_type=CaseType.CORRUPTION,
            title="Test Case",
            slug="original-slug",
        )
        case.contributors.add(admin_user)

        # Add accused entity
        CaseEntityRelationship.objects.create(
            case=case,
            entity=entity,
            relationship_type=RelationshipType.ACCUSED,
        )

        # Try to change slug via PATCH
        response = client.patch(
            f"/api/caseworker/cases/{case.case_id}/",
            data=[
                {"op": "replace", "path": "/title", "value": "Updated Title"},
                {"op": "replace", "path": "/slug", "value": "new-slug"},
            ],
            content_type="application/json",
        )

        # Should return 422 (blocked path) or 400 (validation error)
        assert response.status_code in [400, 422]
        
        # Verify slug was not changed
        case.refresh_from_db()
        assert case.slug == "original-slug"

    def test_patch_slug_blocked_path(self, client, admin_user, entity):
        """PATCH operation targeting /slug path should be blocked."""
        client.force_login(admin_user)

        # Create case with slug
        case = Case.objects.create(
            case_type=CaseType.CORRUPTION,
            title="Test Case",
            slug="original-slug",
        )
        case.contributors.add(admin_user)

        # Add accused entity
        CaseEntityRelationship.objects.create(
            case=case,
            entity=entity,
            relationship_type=RelationshipType.ACCUSED,
        )

        # Try to directly patch slug
        response = client.patch(
            f"/api/caseworker/cases/{case.case_id}/",
            data=[
                {"op": "replace", "path": "/slug", "value": "new-slug"},
            ],
            content_type="application/json",
        )

        # Should return 422 for blocked path
        assert response.status_code == 422
        response_data = response.json()
        assert "slug" in str(response_data).lower() or "blocked" in str(response_data).lower()

    def test_patch_other_fields_with_existing_slug(self, client, admin_user, entity):
        """PATCH can update other fields when slug exists."""
        client.force_login(admin_user)

        # Create case with slug
        case = Case.objects.create(
            case_type=CaseType.CORRUPTION,
            title="Test Case",
            slug="original-slug",
        )
        case.contributors.add(admin_user)

        # Add accused entity
        CaseEntityRelationship.objects.create(
            case=case,
            entity=entity,
            relationship_type=RelationshipType.ACCUSED,
        )

        # Update title (not slug)
        response = client.patch(
            f"/api/caseworker/cases/{case.case_id}/",
            data=[
                {"op": "replace", "path": "/title", "value": "Updated Title"},
            ],
            content_type="application/json",
        )

        assert response.status_code == 200
        case.refresh_from_db()
        assert case.title == "Updated Title"
        assert case.slug == "original-slug"  # Slug unchanged


@pytest.mark.django_db
class TestSlugAutoGeneration:
    """Test automatic slug generation for published cases."""

    def test_publish_without_slug_generates_slug(self, admin_user, entity):
        """Publishing a case without slug should auto-generate one."""
        case = Case.objects.create(
            case_type=CaseType.CORRUPTION,
            title="Test Case for Slug Generation",
            key_allegations=["Allegation 1"],
            description="Test description",
        )
        case.contributors.add(admin_user)

        # Add accused entity
        CaseEntityRelationship.objects.create(
            case=case,
            entity=entity,
            relationship_type=RelationshipType.ACCUSED,
        )

        # Publish without slug
        case.slug = None
        case.publish()

        # Slug should be auto-generated
        assert case.slug is not None
        assert len(case.slug) > 0
        assert case.slug.startswith("test-case-for-slug-generation"[:42])

    def test_publish_with_slug_preserves_slug(self, admin_user, entity):
        """Publishing a case with existing slug should preserve it."""
        case = Case.objects.create(
            case_type=CaseType.CORRUPTION,
            title="Test Case",
            slug="custom-slug",
            key_allegations=["Allegation 1"],
            description="Test description",
        )
        case.contributors.add(admin_user)

        # Add accused entity
        CaseEntityRelationship.objects.create(
            case=case,
            entity=entity,
            relationship_type=RelationshipType.ACCUSED,
        )

        # Publish with existing slug
        case.publish()

        # Slug should be preserved
        assert case.slug == "custom-slug"
