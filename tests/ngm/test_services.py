import pytest

from ngm.services import apply_row_cap, validate_query


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM court_cases",
        "select case_number from court_case_entities",
        "SELECT c.identifier FROM courts c JOIN court_cases cc ON cc.court_identifier = c.identifier",
    ],
)
def test_validate_query_accepts_allowed_select_queries(query):
    is_valid, error = validate_query(query)
    assert is_valid is True
    assert error is None


@pytest.mark.parametrize(
    "query,error_contains",
    [
        ("UPDATE court_cases SET case_type = 'X'", "Only SELECT queries are allowed"),
        ("SELECT * FROM scraped_dates", "scraped_dates"),
        ("SELECT * FROM users", "Invalid table"),
        ("SELECT * FROM court_cases; DELETE FROM court_cases", "Forbidden keyword"),
    ],
)
def test_validate_query_rejects_unsafe_queries(query, error_contains):
    is_valid, error = validate_query(query)
    assert is_valid is False
    assert error_contains in error


def test_apply_row_cap_wraps_query_and_limits_rows():
    query = "SELECT * FROM court_cases ORDER BY registration_date_ad DESC"
    capped = apply_row_cap(query, max_rows=500)
    assert capped.startswith("SELECT * FROM (")
    assert "LIMIT 500" in capped
    assert "ORDER BY registration_date_ad DESC" in capped
