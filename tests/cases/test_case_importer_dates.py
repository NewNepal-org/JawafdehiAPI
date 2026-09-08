"""``CaseImporter`` date mapping — the trial columns and their retired names.

The columns were renamed ``case_*`` → ``trial_*`` in migration 0064. Every
case-result.json written before that rename still carries the old keys, and the
importer read only the new ones: the dates were dropped silently, with a created
case to make it look like the import worked.
"""

import json
import logging
from datetime import date

import pytest

from cases.models import Case
from cases.services.case_importer import CaseImporter

IMPORTER_LOGGER = "cases.services.case_importer"


def _json_file(tmp_path, **fields):
    payload = {"title": "जग्गा प्रकरण", "description": "d"}
    payload.update(fields)
    path = tmp_path / "case-result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


@pytest.mark.django_db
def test_the_new_keys_are_read_without_a_deprecation_warning(tmp_path, caplog):
    path = _json_file(
        tmp_path, trial_start_date="2024-02-25", trial_end_date="2025-08-13"
    )

    with caplog.at_level(logging.WARNING, logger=IMPORTER_LOGGER):
        case = CaseImporter().import_from_json(path)

    case = Case.objects.get(pk=case.pk)
    assert case.trial_start_date == date(2024, 2, 25)
    assert case.trial_end_date == date(2025, 8, 13)
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING] == []


@pytest.mark.django_db
def test_the_retired_keys_still_import_their_dates_with_a_warning(tmp_path, caplog):
    """A pre-rename export must keep its dates, loudly rather than silently."""
    path = _json_file(
        tmp_path, case_start_date="2024-02-25", case_end_date="2025-08-13"
    )

    with caplog.at_level(logging.WARNING, logger=IMPORTER_LOGGER):
        case = CaseImporter().import_from_json(path)

    case = Case.objects.get(pk=case.pk)
    assert case.trial_start_date == date(2024, 2, 25)
    assert case.trial_end_date == date(2025, 8, 13)

    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(
        "case_start_date" in m and "deprecated" in m and "case-result.json" in m
        for m in warnings
    ), warnings
    assert any("case_end_date" in m for m in warnings), warnings


@pytest.mark.django_db
def test_the_new_key_wins_when_a_payload_carries_both(tmp_path):
    path = _json_file(
        tmp_path, trial_start_date="2024-02-25", case_start_date="2019-01-01"
    )

    case = Case.objects.get(pk=CaseImporter().import_from_json(path).pk)
    assert case.trial_start_date == date(2024, 2, 25)


@pytest.mark.django_db
def test_a_payload_with_no_dates_imports_clean(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger=IMPORTER_LOGGER):
        case = CaseImporter().import_from_json(_json_file(tmp_path))

    case = Case.objects.get(pk=case.pk)
    assert (case.trial_start_date, case.trial_end_date) == (None, None)
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING] == []
