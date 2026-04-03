"""
Unit tests for cases.validators module.

Feature: case-model-new-fields
Tests validation functions for slug and court_cases fields.
"""

import pytest
from django.core.exceptions import ValidationError

from cases.validators import (
    validate_slug,
    validate_court_cases,
    VALID_COURT_IDENTIFIERS,
)

# ============================================================================
# validate_slug Tests
# ============================================================================


class TestValidateSlug:
    """Test suite for validate_slug function."""

    def test_valid_slug_with_letters_only(self):
        """Valid slug with only letters should pass."""
        validate_slug("corruption")
        validate_slug("a")
        validate_slug("LalitaNiwas")

    def test_valid_slug_with_letters_and_numbers(self):
        """Valid slug with letters and numbers should pass."""
        validate_slug("corruption-case-2078")
        validate_slug("case123")
        validate_slug("a1b2c3")

    def test_valid_slug_with_hyphens(self):
        """Valid slug with hyphens should pass."""
        validate_slug("land-encroachment-baluwatar")
        validate_slug("lalita-niwas-land-grab")
        validate_slug("wide-body-aircraft-purchase")

    def test_valid_slug_single_character(self):
        """Single letter slug should pass."""
        validate_slug("a")
        validate_slug("Z")

    def test_valid_slug_max_length(self):
        """Slug with exactly 50 characters should pass."""
        # 1 letter + 49 characters = 50 total
        slug = "a" + "b" * 49
        validate_slug(slug)

    def test_invalid_slug_empty_string(self):
        """Empty string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("")
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_invalid_slug_whitespace_only(self):
        """Whitespace-only string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("   ")
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_invalid_slug_starts_with_number(self):
        """Slug starting with number should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("123-case")
        assert "must start with a letter" in str(exc_info.value)

    def test_invalid_slug_starts_with_hyphen(self):
        """Slug starting with hyphen should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("-case")
        assert "must start with a letter" in str(exc_info.value)

    def test_invalid_slug_contains_underscore(self):
        """Slug containing underscore should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("case_name")
        assert "must start with a letter" in str(exc_info.value)

    def test_invalid_slug_contains_space(self):
        """Slug containing space should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("case name")
        assert "must start with a letter" in str(exc_info.value)

    def test_invalid_slug_contains_special_characters(self):
        """Slug containing special characters should raise ValidationError."""
        invalid_slugs = [
            "case@name",
            "case#name",
            "case$name",
            "case%name",
            "case&name",
            "case*name",
            "case(name)",
            "case+name",
            "case=name",
            "case[name]",
            "case{name}",
            "case|name",
            "case\\name",
            "case/name",
            "case:name",
            "case;name",
            "case'name",
            'case"name',
            "case<name>",
            "case,name",
            "case.name",
            "case?name",
        ]
        for slug in invalid_slugs:
            with pytest.raises(ValidationError):
                validate_slug(slug)

    def test_invalid_slug_too_long(self):
        """Slug longer than 50 characters should raise ValidationError."""
        # 1 letter + 50 characters = 51 total
        slug = "a" + "b" * 50
        with pytest.raises(ValidationError) as exc_info:
            validate_slug(slug)
        assert "max 50 characters" in str(exc_info.value)


# ============================================================================
# validate_court_cases Tests
# ============================================================================


class TestValidateCourtCases:
    """Test suite for validate_court_cases function."""

    def test_valid_empty_list(self):
        """Empty list should pass validation."""
        validate_court_cases([])

    def test_valid_single_court_case(self):
        """Single valid court case reference should pass."""
        validate_court_cases(["supreme:2078-CR-0123"])

    def test_valid_multiple_court_cases(self):
        """Multiple valid court case references should pass."""
        validate_court_cases(
            [
                "supreme:2078-CR-0123",
                "district-kathmandu:2077-WO-0456",
                "high-patan:2078-AP-0789",
            ]
        )

    def test_valid_all_court_identifiers(self):
        """All valid court identifiers should pass."""
        court_cases = [f"{court}:2078-TEST-001" for court in VALID_COURT_IDENTIFIERS]
        validate_court_cases(court_cases)

    def test_valid_various_case_number_formats(self):
        """Various case number formats should pass."""
        validate_court_cases(
            [
                "supreme:2078-CR-0123",
                "supreme:123",
                "supreme:ABC-123-XYZ",
                "supreme:case-number-with-many-parts",
            ]
        )

    def test_invalid_not_a_list(self):
        """Non-list value should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases("supreme:2078-CR-0123")
        assert "must be a list" in str(exc_info.value)

    def test_invalid_list_with_non_string_element(self):
        """List with non-string element should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["supreme:2078-CR-0123", 123])
        assert "must be a string" in str(exc_info.value)

    def test_invalid_list_with_dict_element(self):
        """List with dict element should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases([{"court": "supreme", "case": "123"}])
        assert "must be a string" in str(exc_info.value)

    def test_invalid_missing_colon(self):
        """Court case reference without colon should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["supreme-2078-CR-0123"])
        assert "must be in format <court_identifier>:<case_number>" in str(
            exc_info.value
        )

    def test_invalid_multiple_colons(self):
        """Court case reference with multiple colons should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["supreme:2078:CR:0123"])
        assert "must be in format <court_identifier>:<case_number>" in str(
            exc_info.value
        )

    def test_invalid_court_identifier(self):
        """Unknown court identifier should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["invalid-court:123"])
        assert "Invalid court identifier 'invalid-court'" in str(exc_info.value)
        assert "Valid identifiers are:" in str(exc_info.value)

    def test_invalid_court_identifier_case_sensitive(self):
        """Court identifier is case-sensitive."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["Supreme:123"])
        assert "Invalid court identifier 'Supreme'" in str(exc_info.value)

    def test_invalid_court_identifier_with_typo(self):
        """Court identifier with typo should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["suprme:123"])  # Missing 'e'
        assert "Invalid court identifier 'suprme'" in str(exc_info.value)

    def test_invalid_mixed_valid_and_invalid(self):
        """List with mix of valid and invalid should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_court_cases(
                [
                    "supreme:2078-CR-0123",
                    "invalid-court:456",
                ]
            )

    def test_error_message_includes_valid_identifiers(self):
        """Error message should list all valid court identifiers."""
        with pytest.raises(ValidationError) as exc_info:
            validate_court_cases(["unknown:123"])

        error_message = str(exc_info.value)
        for court in VALID_COURT_IDENTIFIERS:
            assert court in error_message


# ============================================================================
# VALID_COURT_IDENTIFIERS Tests
# ============================================================================


class TestValidCourtIdentifiers:
    """Test suite for VALID_COURT_IDENTIFIERS constant."""

    def test_constant_is_list(self):
        """VALID_COURT_IDENTIFIERS should be a list."""
        assert isinstance(VALID_COURT_IDENTIFIERS, list)

    def test_constant_has_expected_courts(self):
        """VALID_COURT_IDENTIFIERS should contain expected court identifiers."""
        expected_courts = [
            "supreme",
            "high-patan",
            "high-surkhet",
            "district-kathmandu",
            "district-lalitpur",
            "district-bhaktapur",
        ]
        assert VALID_COURT_IDENTIFIERS == expected_courts

    def test_constant_has_six_courts(self):
        """VALID_COURT_IDENTIFIERS should contain exactly 6 courts."""
        assert len(VALID_COURT_IDENTIFIERS) == 6

    def test_constant_no_duplicates(self):
        """VALID_COURT_IDENTIFIERS should not contain duplicates."""
        assert len(VALID_COURT_IDENTIFIERS) == len(set(VALID_COURT_IDENTIFIERS))
