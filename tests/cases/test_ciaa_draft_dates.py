"""The CIAA draft importer's date mapping.

``import_case`` writes through ``Case.objects.create()``, which runs no
validation, so a backwards court-record date has to be caught here or it lands
in production (two rows did).
"""

import logging
from datetime import date

import pytest

from cases.models import Case
from cases.services.ciaa_draft_case_service import CIAADraftCaseService

NGM_DETAILS = "cases.services.ngm_court_records.get_court_case_details"


def _ciaa_json(**court_case_overrides):
    court_case = {
        "court": "special",
        "case_no": "081-CR-0009",
        "registration_date_ad": "2024-02-25",
    }
    court_case.update(court_case_overrides)
    return {
        "case_no": "081-CR-0009",
        "case_title": "Backwards court dates",
        "meta": {"match_status": "confirmed"},
        "court_case": court_case,
    }


@pytest.mark.django_db
def test_backwards_faisala_date_is_dropped_and_logged(monkeypatch, caplog):
    """A verdict before the registration is unusable: keep the case, drop the date."""
    # The roster guard reads NGM; stub it so the import needs no network and
    # logs no warning of its own.
    monkeypatch.setattr(
        NGM_DETAILS, lambda court, case_no: {"case": {"defendant": "एक प्रतिवादी"}}
    )

    with caplog.at_level(logging.WARNING, logger="cases.services.ciaa_draft_case_service"):
        result = CIAADraftCaseService().import_case(
            _ciaa_json(faisala_date_ad="2024-02-01")
        )

    assert result.status == "created", result.errors
    case = Case.objects.get(slug=result.case_id)
    assert case.trial_start_date == date(2024, 2, 25)
    assert case.trial_end_date is None

    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(
        "081-CR-0009" in m and "2024-02-01" in m and "2024-02-25" in m
        for m in warnings
    ), warnings


@pytest.mark.django_db
def test_ordered_faisala_date_is_kept(monkeypatch):
    """The guard only fires on a backwards pair."""
    monkeypatch.setattr(
        NGM_DETAILS, lambda court, case_no: {"case": {"defendant": "एक प्रतिवादी"}}
    )

    result = CIAADraftCaseService().import_case(
        _ciaa_json(faisala_date_ad="2024-06-04")
    )

    case = Case.objects.get(slug=result.case_id)
    assert case.trial_start_date == date(2024, 2, 25)
    assert case.trial_end_date == date(2024, 6, 4)
