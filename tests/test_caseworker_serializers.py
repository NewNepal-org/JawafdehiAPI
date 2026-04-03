"""
Tests for caseworker serializers.

Tests validation and normalization of Case fields in API serializers.
"""

import pytest
from rest_framework.exceptions import ValidationError as DRFValidationError

from cases.caseworker_serializers import CaseCreateSerializer, CasePatchSerializer
from cases.models import CaseState, CaseType


class TestCaseCreateSerializer:
    """Test CaseCreateSerializer validation."""

    def test_create_with_valid_slug(self):
        """Valid slug should pass validation."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "slug": "test-case-slug",
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_invalid_slug(self):
        """Invalid slug should fail validation."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "slug": "123-invalid",  # Starts with number
        }
        serializer = CaseCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "slug" in serializer.errors

    def test_create_with_empty_slug(self):
        """Empty slug should be accepted (optional field)."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "slug": "",
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_null_slug(self):
        """Null slug should be accepted (optional field)."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "slug": None,
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_without_slug(self):
        """Slug can be omitted."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_valid_court_cases(self):
        """Valid court_cases list should pass validation."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "court_cases": ["supreme:2078-CR-0123", "special:2077-WO-0456"],
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_invalid_court_cases(self):
        """Invalid court_cases should fail validation."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "court_cases": ["invalid-court:123"],
        }
        serializer = CaseCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "court_cases" in serializer.errors

    def test_create_with_empty_court_cases(self):
        """Empty court_cases list should be accepted."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "court_cases": [],
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_null_court_cases(self):
        """Null court_cases should be accepted."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "court_cases": None,
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_missing_details(self):
        """Non-empty missing_details should be accepted."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "missing_details": "Missing witness statements",
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_empty_missing_details(self):
        """Empty missing_details should be accepted."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "missing_details": "",
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_null_missing_details(self):
        """Null missing_details should be accepted."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "missing_details": None,
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_bigo(self):
        """Bigo field should accept positive integers."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "bigo": 1000000,
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_with_null_bigo(self):
        """Null bigo should be accepted."""
        data = {
            "case_type": CaseType.CORRUPTION,
            "title": "Test Case",
            "bigo": None,
        }
        serializer = CaseCreateSerializer(data=data)
        assert serializer.is_valid()


class TestCasePatchSerializer:
    """Test CasePatchSerializer validation."""

    def test_patch_with_valid_court_cases(self):
        """Valid court_cases list should pass validation."""
        data = {
            "title": "Updated Title",
            "case_type": CaseType.CORRUPTION,
            "court_cases": ["supreme:2078-CR-0123"],
        }
        serializer = CasePatchSerializer(data=data)
        assert serializer.is_valid()

    def test_patch_with_invalid_court_cases(self):
        """Invalid court_cases should fail validation."""
        data = {
            "title": "Updated Title",
            "case_type": CaseType.CORRUPTION,
            "court_cases": ["invalid:123"],
        }
        serializer = CasePatchSerializer(data=data)
        assert not serializer.is_valid()
        assert "court_cases" in serializer.errors

    def test_patch_with_empty_missing_details(self):
        """Empty missing_details should be accepted."""
        data = {
            "title": "Updated Title",
            "case_type": CaseType.CORRUPTION,
            "missing_details": "",
        }
        serializer = CasePatchSerializer(data=data)
        assert serializer.is_valid()

    def test_patch_with_null_missing_details(self):
        """Null missing_details should be accepted."""
        data = {
            "title": "Updated Title",
            "case_type": CaseType.CORRUPTION,
            "missing_details": None,
        }
        serializer = CasePatchSerializer(data=data)
        assert serializer.is_valid()

    def test_patch_with_bigo(self):
        """Bigo field should accept positive integers."""
        data = {
            "title": "Updated Title",
            "case_type": CaseType.CORRUPTION,
            "bigo": 5000000,
        }
        serializer = CasePatchSerializer(data=data)
        assert serializer.is_valid()

    def test_patch_with_null_bigo(self):
        """Null bigo should be accepted."""
        data = {
            "title": "Updated Title",
            "case_type": CaseType.CORRUPTION,
            "bigo": None,
        }
        serializer = CasePatchSerializer(data=data)
        assert serializer.is_valid()
