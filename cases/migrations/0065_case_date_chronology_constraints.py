# The database backstop for the rule in ``cases/chronology.py``. Only the
# writers that validate reach that rule: ``objects.create()``, the PATCH
# endpoint's bulk ``update()``, the seed command and raw SQL do not, which is
# how two production drafts came to hold a verdict date earlier than their
# registration date. Those rows are nulled first — a check constraint cannot be
# added to a table that violates it.
#
# Pairwise only, deliberately: the transitive comparison ("an appeal date is not
# before ``trial_end_date`` OR ELSE ``trial_start_date``") has no clean NULL-safe
# spelling as a check constraint, and it stays a validation-layer rule.

from django.db import migrations, models
from django.db.models import F, Q


def null_backwards_trial_end(apps, schema_editor):
    """Null every ``trial_end_date`` that precedes its ``trial_start_date``, printing the slug."""
    case_model = apps.get_model("cases", "Case")
    backwards = case_model.objects.filter(
        trial_start_date__isnull=False,
        trial_end_date__isnull=False,
        trial_end_date__lt=F("trial_start_date"),
    )
    # Printed, not logged: migrations run before any logging configuration this
    # project sets up, so a logger call would be silently dropped and the
    # operator would never learn which rows lost a date.
    for slug, start, end in backwards.values_list(
        "slug", "trial_start_date", "trial_end_date"
    ):
        print(
            f"0065: dropping backwards trial_end_date {end} "
            f"(trial start {start}) on case {slug}"
        )
    backwards.update(trial_end_date=None)


def keep_the_nulled_dates(apps, schema_editor):
    """No-op: the dropped values were invalid, and nothing recorded them."""


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0064_case_trial_and_appeal_dates"),
    ]

    operations = [
        migrations.RunPython(null_backwards_trial_end, keep_the_nulled_dates),
        migrations.AddConstraint(
            model_name="case",
            constraint=models.CheckConstraint(
                condition=Q(trial_start_date__isnull=True)
                | Q(trial_end_date__isnull=True)
                | Q(trial_end_date__gte=F("trial_start_date")),
                name="case_trial_end_not_before_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="case",
            constraint=models.CheckConstraint(
                condition=Q(appeal_start_date__isnull=True)
                | Q(appeal_end_date__isnull=True)
                | Q(appeal_end_date__gte=F("appeal_start_date")),
                name="case_appeal_end_not_before_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="case",
            constraint=models.CheckConstraint(
                condition=Q(trial_end_date__isnull=True)
                | Q(appeal_start_date__isnull=True)
                | Q(appeal_start_date__gte=F("trial_end_date")),
                name="case_appeal_start_not_before_trial_end",
            ),
        ),
    ]
