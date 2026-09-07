"""Migration 0065 — the database backstop for the trial/appeal date chronology.

``cases.chronology`` holds the rule, but only the writers that validate reach
it: ``Case.objects.create()`` (the CIAA importer, the seed command, a shell),
``QuerySet.update()`` (the PATCH endpoint's bulk write) and raw SQL all go
straight to the table. Two production drafts hold a verdict date earlier than
their registration date because of that, which is why the migration nulls those
rows before it adds the constraints.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from cases.models import Case, CaseState, CaseType

BEFORE = ("cases", "0064_case_trial_and_appeal_dates")
AFTER = ("cases", "0065_case_date_chronology_constraints")


@contextmanager
def _rolled_back_to_0064():
    """Put the cases app back on 0064 for the block, then re-apply 0065.

    The suite's database is fully migrated, so the only way to hold a row 0065's
    data step would have to fix is to unapply 0065 first — which is also what
    makes this the migration itself under test rather than a copy of its logic.
    The re-apply is unconditional: leaving the session's database without the
    constraints would fail every later test for the wrong reason.
    """
    executor = MigrationExecutor(connection)
    executor.migrate([BEFORE])
    try:
        yield
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate([AFTER])


def _case(**kwargs) -> Case:
    defaults = dict(
        title="Backwards dates",
        case_type=CaseType.CORRUPTION,
        state=CaseState.DRAFT,
    )
    defaults.update(kwargs)
    return Case.objects.create(**defaults)


@pytest.mark.django_db(transaction=True)
def test_0065_nulls_a_backwards_trial_end_and_prints_the_slug(capsys):
    """The data step: a row 0065 cannot constrain until it has fixed it."""
    with _rolled_back_to_0064():
        _case(
            slug="backwards-verdict-draft",
            trial_start_date=date(2024, 2, 25),
            trial_end_date=date(2024, 2, 1),
        )
        # An untouched neighbour: the data step must be surgical.
        _case(
            title="Ordered dates",
            slug="ordered-verdict-draft",
            trial_start_date=date(2024, 2, 25),
            trial_end_date=date(2024, 6, 4),
        )
        capsys.readouterr()

    fixed = Case.objects.get(slug="backwards-verdict-draft")
    ordered = Case.objects.get(slug="ordered-verdict-draft")
    assert fixed.trial_end_date is None
    assert fixed.trial_start_date == date(2024, 2, 25)
    assert ordered.trial_end_date == date(2024, 6, 4)

    printed = capsys.readouterr().out
    assert "backwards-verdict-draft" in printed
    assert "2024-02-01" in printed
    assert "ordered-verdict-draft" not in printed


@pytest.mark.django_db
def test_the_orm_cannot_create_a_backwards_trial():
    """``Case.objects.create()`` runs no validation — the constraint is the net."""
    with pytest.raises(IntegrityError), transaction.atomic():
        _case(
            slug="orm-backwards-trial",
            trial_start_date=date(2024, 2, 25),
            trial_end_date=date(2024, 2, 1),
        )


@pytest.mark.django_db
def test_the_orm_cannot_create_a_backwards_appeal():
    with pytest.raises(IntegrityError), transaction.atomic():
        _case(
            slug="orm-backwards-appeal",
            appeal_start_date=date(2025, 8, 13),
            appeal_end_date=date(2025, 8, 1),
        )


@pytest.mark.django_db
def test_the_orm_cannot_create_an_appeal_before_the_verdict():
    with pytest.raises(IntegrityError), transaction.atomic():
        _case(
            slug="orm-premature-appeal",
            trial_end_date=date(2025, 8, 13),
            appeal_start_date=date(2025, 8, 1),
        )


@pytest.mark.django_db
def test_a_case_that_knows_only_some_of_its_dates_still_saves():
    """Every constraint is nullable-aware: a half-known case is valid, not a 500."""
    case = _case(slug="half-known-dates", trial_start_date=date(2024, 2, 25))
    case.refresh_from_db()
    assert (case.trial_end_date, case.appeal_start_date, case.appeal_end_date) == (
        None,
        None,
        None,
    )
