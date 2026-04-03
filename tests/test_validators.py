"""
Tests for cases.validators module.

Tests validation functions for Case model fields including slug and court_cases.
"""

import pytest
from django.core.exceptions import ValidationError

from cases.validators import validate_slug, validate_court_cases, VALID_COURT_IDENTIFIERS


class TestValidateSlug:
    """Test validate_slug function."""

    def test_valid_slug_with_letters_only(self):
        """Valid slug with only letters should pass."""
        validate_slug("corruption")
        validate_slug("a")
        validate_slug("ABC")

    def test_valid_slug_with_letters_and_numbers(self):
        """Valid slug with letters and numbers should pass."""
        validate_slug("case123")
        validate_slug("corruption2078")
        validate_slug("a1b2c3")

    def test_valid_slug_with_hyphens(self):
        """Valid slug with hyphens should pass."""
        validate_slug("corruption-case")
        validate_slug("land-encroachment-baluwatar")
        validate_slug("case-2078-corruption")

    def test_valid_slug_max_length(self):
        """Valid slug at max length (50 chars) should pass."""
        slug_50_chars = "a" + "b" * 49
        validate_slug(slug_50_chars)

    def test_invalid_slug_starts_with_number(self):
        """Slug starting with number should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("123case")
        assert "must start with a letter" in str(exc_info.value)

    def test_invalid_slug_starts_with_hyphen(self):
        """Slug starting with hyphen should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("-case")
        assert "must start with a letter" in str(exc_info.value)

    def test_invalid_slug_with_underscore(self):
        """Slug with underscore should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("case_name")
        assert "must start with a letter" in str(exc_info.value)

    def test_invalid_slug_with_space(self):
        """Slug with space should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("case name")
        assert "must start with a letter" in str(exc_info.value)

    def test_invalid_slug_empty_string(self):
        """Empty string should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("")
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_invalid_slug_whitespace_only(self):
        """Whitespace-only string should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("   ")
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_invalid_slug_exceeds_max_length(self):
        """Slug exceeding 50 characters should fail."""
        slug_51_chars = "a" + "b" * 50
        with pytest.raises(ValidationError) as exc_info:
            validate_slug(slug_51_chars)
        assert "max 50 characters" in str(exc_info.value)

    def test_invalid_slug_with_special_chars(self):
        """Slug with special characters should fail."""
        invalid_slugs = [
            "case@name",
            "case#name",
            "case$name",
            "case%name",
            "case&name",
            "case*name",
            "case(name)",
            "case[name]",
            "case{name}",
        ]
        for slug in invalid_slugs:
            with pytest.raises(ValidationError):
                validate_slug(slug)


class TestValidateCourtCases:
    """Test validate_court_cases function."""

    def test_valid_empty_list(self):
        """Empty list should pass."""
        validate_court_cases([])

    def test_valid_single_court_case(self):
        """Single valid court case should pass."""
        validate_court_cases(["supreme:2078-CR-0123"])

    def test_valid_multiple_court_cases(self):
        """Multiple valid court cases should pass."""
        validate_court_cases([
            "supreme:2078-CR-0123",
            "special:2077-WO-0456",
        ])

    def test_valid_all_court_identifiers(self):
        """All valid court identifiers should pass."""
        for court_id in VALID_COURT_IDENTIFIERS:
            validate_court_cases([f"{court_id}:2078-CR-0123"])

    def test_invalid_not_a_list(self):
        """Non-list value should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases("supreme:2078-CR-0123")
        assert "must be a list" in str(exc_info.value)

    def test_invalid_element_not_string(self):
        """Non-string element should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases([123])
        assert "must be a string" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases([{"court": "supreme", "case": "123"}])
        assert "must be a string" in str(exc_info.value)

    def test_invalid_missing_colon(self):
        """Court case without colon should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["supreme-2078-CR-0123"])
        assert "must be in format <court_identifier>:<case_number>" in str(exc_info.value)

    def test_invalid_multiple_colons(self):
        """Court case with multiple colons should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["supreme:2078:CR:0123"])
        assert "must be in format <court_identifier>:<case_number>" in str(exc_info.value)

    def test_invalid_court_identifier(self):
        """Invalid court identifier should fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["invalid-court:2078-CR-0123"])
        assert "Invalid court identifier" in str(exc_info.value)
        assert "invalid-court" in str(exc_info.value)

    def test_invalid_court_identifier_shows_valid_list(self):
        """Error message should show valid court identifiers."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["unknown:123"])
        error_msg = str(exc_info.value)
        assert "Valid identifiers are:" in error_msg
        for court_id in VALID_COURT_IDENTIFIERS:
            assert court_id in error_msg
