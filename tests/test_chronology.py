"""``cases.chronology.date_chronology_errors`` — the one trial/appeal date rule.

The rule is transitive: an appeal date is compared against the latest trial date
the case knows (the verdict, else the registration), and ``appeal_end_date``
falls back to that same date when no appeal start is recorded. Three copies of a
pairwise-only version used to live in the model, the write serializer and the
CIAA importer, and each of them accepted an appeal that predates the trial.

Every cell is asserted twice: once against the function, once through
``Case._date_chronology_errors``, which is the model's only copy of the rule.
"""

from datetime import date

import pytest

from cases.chronology import date_chronology_errors
from cases.models import Case, CaseState


def _both(trial_start, trial_end, appeal_start, appeal_end):
    """The rule's verdict from the function and from the model, asserted equal."""
    direct = date_chronology_errors(trial_start, trial_end, appeal_start, appeal_end)
    via_model = Case(
        title="t",
        state=CaseState.DRAFT,
        trial_start_date=trial_start,
        trial_end_date=trial_end,
        appeal_start_date=appeal_start,
        appeal_end_date=appeal_end,
    )._date_chronology_errors()
    assert direct == via_model, "the model must not carry its own copy of the rule"
    return direct


def test_an_appeal_before_the_trial_start_is_rejected_with_no_verdict_date():
    """The transitive cell: no ``trial_end_date``, so the registration is the anchor.

    A case with a trial start and no verdict yet is the shape the appeal dates
    exist for, and the pairwise rule accepted any appeal date at all on it.
    """
    errors = _both(date(2024, 2, 25), None, date(2023, 1, 1), None)
    assert errors == {
        "appeal_start_date": "Appeal start date is before the trial start date"
    }


def test_an_appeal_end_before_the_verdict_is_rejected_with_no_appeal_start():
    """An appellate verdict older than the first-instance one, with no appeal start."""
    errors = _both(date(2024, 2, 25), date(2025, 8, 13), None, date(2025, 1, 1))
    assert errors == {
        "appeal_end_date": "Appeal end date is before the trial end date"
    }


def test_an_appeal_end_before_the_trial_start_is_rejected_with_neither_anchor():
    """No trial end and no appeal start: the appeal end still has the registration."""
    errors = _both(date(2024, 2, 25), None, None, date(2023, 12, 1))
    assert errors == {
        "appeal_end_date": "Appeal end date is before the trial start date"
    }


def test_a_consistent_set_of_four_dates_has_no_errors():
    errors = _both(
        date(2024, 2, 25), date(2025, 8, 13), date(2025, 9, 1), date(2026, 3, 4)
    )
    assert errors == {}


def test_a_case_that_knows_nothing_is_valid():
    assert _both(None, None, None, None) == {}


@pytest.mark.parametrize(
    ("trial_start", "trial_end", "appeal_start", "appeal_end", "expected"),
    [
        # The three pairwise cells the DB constraints mirror, unchanged.
        (
            date(2024, 2, 25),
            date(2024, 2, 1),
            None,
            None,
            {"trial_end_date": "Trial end date is before the trial start date"},
        ),
        (
            None,
            date(2025, 8, 13),
            date(2025, 8, 1),
            None,
            {"appeal_start_date": "Appeal start date is before the trial end date"},
        ),
        (
            None,
            None,
            date(2025, 8, 13),
            date(2025, 8, 1),
            {"appeal_end_date": "Appeal end date is before the appeal start date"},
        ),
    ],
)
def test_the_pairwise_cells_keep_their_messages(
    trial_start, trial_end, appeal_start, appeal_end, expected
):
    """The existing error keys and wording are contract — the SPA renders them."""
    assert _both(trial_start, trial_end, appeal_start, appeal_end) == expected


def test_at_most_one_error_per_field():
    """Every rule for a field is one message: the SPA attaches one per input."""
    errors = _both(
        date(2024, 2, 25), date(2024, 2, 1), date(2023, 1, 1), date(2022, 1, 1)
    )
    assert set(errors) == {"trial_end_date", "appeal_start_date", "appeal_end_date"}
    assert all(isinstance(message, str) for message in errors.values())
