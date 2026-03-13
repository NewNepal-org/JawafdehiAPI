"""
TDD tests for entity-cases relationship in Entity API.

Feature: Entity Cases Relationship
Tests that entity detail endpoint returns alleged_cases and related_cases lists.
Now returns public case_id strings (not internal DB PKs).
"""

import pytest
from rest_framework.test import APIClient

from cases.models import Case, CaseEntityRelationship, CaseState, JawafEntity


def _add_alleged(case, *entities):
    """Helper: add entity as alleged to case via CaseEntityRelationship through model."""
    for entity in entities:
        CaseEntityRelationship.objects.get_or_create(
            case=case,
            entity=entity,
            type=CaseEntityRelationship.RelationshipType.ALLEGED,
        )


def _add_related(case, *entities):
    """Helper: add entity as related to case via CaseEntityRelationship through model."""
    for entity in entities:
        CaseEntityRelationship.objects.get_or_create(
            case=case,
            entity=entity,
            type=CaseEntityRelationship.RelationshipType.RELATED,
        )


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


# ============================================================================
# Basic Functionality Tests
# ============================================================================


@pytest.mark.django_db
def test_entity_detail_includes_alleged_cases_field():
    """Test that entity detail response includes alleged_cases field."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test-person")

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert "alleged_cases" in response.data


@pytest.mark.django_db
def test_entity_detail_includes_related_cases_field():
    """Test that entity detail response includes related_cases field."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test-person")

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert "related_cases" in response.data


@pytest.mark.django_db
def test_entity_with_no_cases_returns_empty_lists():
    """Test that entity with no cases returns empty lists."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test-person")

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert response.data["alleged_cases"] == []
    assert response.data["related_cases"] == []


# ============================================================================
# Alleged Cases Tests
# ============================================================================


@pytest.mark.django_db
def test_entity_alleged_in_published_case():
    """Test that entity shows case_id string when alleged in published case."""
    entity = JawafEntity.objects.create(nes_id="entity:person/accused")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test description",
    )
    _add_alleged(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case.case_id in response.data["alleged_cases"]
    assert len(response.data["alleged_cases"]) == 1


@pytest.mark.django_db
def test_entity_alleged_in_multiple_published_cases():
    """Test that entity shows all case_id strings when alleged in multiple cases."""
    entity = JawafEntity.objects.create(nes_id="entity:person/accused")

    case1 = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Case 1",
        description="Test",
    )
    _add_alleged(case1, entity)

    case2 = Case.objects.create(
        case_id="case-002",
        state=CaseState.PUBLISHED,
        title="Case 2",
        description="Test",
    )
    _add_alleged(case2, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case1.case_id in response.data["alleged_cases"]
    assert case2.case_id in response.data["alleged_cases"]
    assert len(response.data["alleged_cases"]) == 2


@pytest.mark.django_db
def test_entity_alleged_in_draft_case_not_included():
    """Test that draft cases are not included in alleged_cases."""
    entity = JawafEntity.objects.create(nes_id="entity:person/accused")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.DRAFT,
        title="Draft Case",
        description="Test",
    )
    _add_alleged(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert response.data["alleged_cases"] == []


@pytest.mark.django_db
def test_entity_alleged_in_closed_case_not_included():
    """Test that closed cases are not included in alleged_cases."""
    entity = JawafEntity.objects.create(nes_id="entity:person/accused")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.CLOSED,
        title="Closed Case",
        description="Test",
    )
    _add_alleged(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert response.data["alleged_cases"] == []


# ============================================================================
# Related Cases Tests
# ============================================================================


@pytest.mark.django_db
def test_entity_related_in_published_case():
    """Test that entity shows case_id string when related in published case."""
    entity = JawafEntity.objects.create(nes_id="entity:person/related")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    _add_related(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case.case_id in response.data["related_cases"]
    assert len(response.data["related_cases"]) == 1


@pytest.mark.django_db
def test_entity_location_in_published_case():
    """Test that entity shows case_id when used as location in published case."""
    entity = JawafEntity.objects.create(nes_id="entity:location/kathmandu")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    case.locations.add(entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case.case_id in response.data["related_cases"]
    assert len(response.data["related_cases"]) == 1


@pytest.mark.django_db
def test_entity_related_and_location_in_same_case():
    """Test that entity appears once when both related and location in same case."""
    entity = JawafEntity.objects.create(nes_id="entity:organization/test-org")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    _add_related(case, entity)
    case.locations.add(entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    # Should appear only once even though in both fields
    assert response.data["related_cases"].count(case.case_id) == 1


@pytest.mark.django_db
def test_entity_related_in_draft_case_not_included():
    """Test that draft cases are not included in related_cases."""
    entity = JawafEntity.objects.create(nes_id="entity:person/related")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.DRAFT,
        title="Draft Case",
        description="Test",
    )
    _add_related(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert response.data["related_cases"] == []


# ============================================================================
# Alleged vs Related Separation Tests
# ============================================================================


@pytest.mark.django_db
def test_entity_alleged_not_in_related_cases():
    """Test that alleged cases don't appear in related_cases."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    _add_alleged(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case.case_id in response.data["alleged_cases"]
    assert case.case_id not in response.data["related_cases"]


@pytest.mark.django_db
def test_entity_both_alleged_and_related_in_same_case():
    """Test that case appears only in alleged_cases when entity has both relationship types."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    _add_alleged(case, entity)
    _add_related(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case.case_id in response.data["alleged_cases"]
    assert case.case_id not in response.data["related_cases"]


@pytest.mark.django_db
def test_entity_both_alleged_and_location_in_same_case():
    """Test that case appears only in alleged_cases when entity is both alleged and location."""
    entity = JawafEntity.objects.create(nes_id="entity:location/test")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    _add_alleged(case, entity)
    case.locations.add(entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case.case_id in response.data["alleged_cases"]
    assert case.case_id not in response.data["related_cases"]


# ============================================================================
# Complex Scenarios
# ============================================================================


@pytest.mark.django_db
def test_entity_in_multiple_cases_with_different_roles():
    """Test entity appearing in different roles across multiple cases."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case1 = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Case 1",
        description="Test",
    )
    _add_alleged(case1, entity)

    case2 = Case.objects.create(
        case_id="case-002",
        state=CaseState.PUBLISHED,
        title="Case 2",
        description="Test",
    )
    _add_related(case2, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case1.case_id in response.data["alleged_cases"]
    assert case2.case_id in response.data["related_cases"]
    assert len(response.data["alleged_cases"]) == 1
    assert len(response.data["related_cases"]) == 1


@pytest.mark.django_db
def test_entity_with_mix_of_published_and_draft_cases():
    """Test that only published cases appear in the lists."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    published_case = Case.objects.create(
        case_id="case-published",
        state=CaseState.PUBLISHED,
        title="Published Case",
        description="Test",
    )
    _add_alleged(published_case, entity)

    draft_case = Case.objects.create(
        case_id="case-draft",
        state=CaseState.DRAFT,
        title="Draft Case",
        description="Test",
    )
    _add_alleged(draft_case, entity)

    closed_case = Case.objects.create(
        case_id="case-closed",
        state=CaseState.CLOSED,
        title="Closed Case",
        description="Test",
    )
    _add_related(closed_case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert published_case.case_id in response.data["alleged_cases"]
    assert draft_case.case_id not in response.data["alleged_cases"]
    assert closed_case.case_id not in response.data["related_cases"]
    assert len(response.data["alleged_cases"]) == 1
    assert len(response.data["related_cases"]) == 0
    assert len(response.data["related_cases"]) == 0


# ============================================================================
# Feature Flag Tests (EXPOSE_CASES_IN_REVIEW)
# ============================================================================


@pytest.mark.django_db
def test_in_review_cases_included_when_feature_flag_enabled(settings):
    """Test that IN_REVIEW cases are included when EXPOSE_CASES_IN_REVIEW is True."""
    settings.EXPOSE_CASES_IN_REVIEW = True

    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.IN_REVIEW,
        title="In Review Case",
        description="Test",
    )
    _add_alleged(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case.case_id in response.data["alleged_cases"]


@pytest.mark.django_db
def test_in_review_cases_excluded_when_feature_flag_disabled(settings):
    """Test that IN_REVIEW cases are excluded when EXPOSE_CASES_IN_REVIEW is False."""
    settings.EXPOSE_CASES_IN_REVIEW = False

    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.IN_REVIEW,
        title="In Review Case",
        description="Test",
    )
    _add_alleged(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert case.case_id not in response.data["alleged_cases"]
    assert response.data["alleged_cases"] == []


# ============================================================================
# Data Type Tests — now returns case_id strings, not integer PKs
# ============================================================================


@pytest.mark.django_db
def test_alleged_cases_is_list_of_strings():
    """Test that alleged_cases returns a list of case_id strings (not int PKs)."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    _add_alleged(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert isinstance(response.data["alleged_cases"], list)
    assert all(isinstance(cid, str) for cid in response.data["alleged_cases"])
    assert response.data["alleged_cases"] == ["case-001"]


@pytest.mark.django_db
def test_related_cases_is_list_of_strings():
    """Test that related_cases returns a list of case_id strings (not int PKs)."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    _add_related(case, entity)

    client = APIClient()
    response = client.get(f"/api/entities/{entity.id}/")

    assert response.status_code == 200
    assert isinstance(response.data["related_cases"], list)
    assert all(isinstance(cid, str) for cid in response.data["related_cases"])
    assert response.data["related_cases"] == ["case-001"]


# ============================================================================
# List Endpoint Tests
# ============================================================================


@pytest.mark.django_db
def test_entity_list_includes_case_fields():
    """Test that entity list endpoint includes alleged_cases and related_cases fields."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Test Case",
        description="Test",
    )
    _add_alleged(case, entity)

    client = APIClient()
    response = client.get("/api/entities/")

    assert response.status_code == 200
    assert len(response.data["results"]) > 0

    entity_data = next(e for e in response.data["results"] if e["id"] == entity.id)
    assert "alleged_cases" in entity_data
    assert "related_cases" in entity_data


@pytest.mark.django_db
def test_entity_list_shows_correct_case_ids():
    """Test that entity list shows correct case_id strings for each entity."""
    entity = JawafEntity.objects.create(nes_id="entity:person/test")

    case1 = Case.objects.create(
        case_id="case-001",
        state=CaseState.PUBLISHED,
        title="Alleged Case",
        description="Test",
    )
    _add_alleged(case1, entity)

    case2 = Case.objects.create(
        case_id="case-002",
        state=CaseState.PUBLISHED,
        title="Related Case",
        description="Test",
    )
    _add_related(case2, entity)

    client = APIClient()
    response = client.get("/api/entities/")

    assert response.status_code == 200
    entity_data = next(e for e in response.data["results"] if e["id"] == entity.id)

    assert case1.case_id in entity_data["alleged_cases"]
    assert case2.case_id in entity_data["related_cases"]
    assert len(entity_data["alleged_cases"]) == 1
    assert len(entity_data["related_cases"]) == 1
