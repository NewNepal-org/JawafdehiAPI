"""The one date-ordering rule for a case's trial and appeal stages.

Every writer calls ``date_chronology_errors``: ``Case.clean()`` /
``Case.validate()``, ``CaseWriteFieldsSerializer.validate()`` and the CIAA
draft importer. Keeping it here is what stops the three copies from drifting;
migration 0065 mirrors the pairwise half of it as DB check constraints.
"""

from __future__ import annotations

from datetime import date


def _before(first: date | None, second: date | None) -> bool:
    """True when both dates are known and ``first`` precedes ``second``."""
    return first is not None and second is not None and first < second


def date_chronology_errors(
    trial_start: date | None,
    trial_end: date | None,
    appeal_start: date | None,
    appeal_end: date | None,
) -> dict[str, str]:
    """Field-keyed errors for the trial/appeal date order (empty when the dates are fine)."""
    errors: dict[str, str] = {}
    if _before(trial_end, trial_start):
        errors["trial_end_date"] = "Trial end date is before the trial start date"

    # The latest trial date the case knows: the verdict when it has one, else
    # the registration. An appeal date is compared against THAT, so a case with
    # no recorded verdict still rejects an appeal filed before its trial began.
    latest_trial = trial_end or trial_start
    trial_label = "trial end" if trial_end else "trial start"

    if _before(appeal_start, latest_trial):
        errors["appeal_start_date"] = (
            f"Appeal start date is before the {trial_label} date"
        )

    if appeal_start is not None:
        if _before(appeal_end, appeal_start):
            errors["appeal_end_date"] = (
                "Appeal end date is before the appeal start date"
            )
    elif _before(appeal_end, latest_trial):
        errors["appeal_end_date"] = f"Appeal end date is before the {trial_label} date"

    return errors
