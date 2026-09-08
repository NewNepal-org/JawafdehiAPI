# Hand-written. The autodetector proposed a remove-and-add pair, which would
# drop every stored date: it only offers a rename when the old and new fields
# deconstruct identically, and the help_text was rewritten in the same edit.
# Renaming the columns in place keeps the values.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0063_case_tags_source"),
    ]

    operations = [
        migrations.RenameField(
            model_name="case",
            old_name="case_start_date",
            new_name="trial_start_date",
        ),
        migrations.RenameField(
            model_name="case",
            old_name="case_end_date",
            new_name="trial_end_date",
        ),
        migrations.AlterField(
            model_name="case",
            name="trial_start_date",
            field=models.DateField(
                blank=True,
                help_text="Registration date at the first-instance court (Special Court for CIAA cases)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="case",
            name="trial_end_date",
            field=models.DateField(
                blank=True,
                help_text="Verdict date at the first-instance court",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="appeal_start_date",
            field=models.DateField(
                blank=True,
                help_text="Registration date of the Supreme Court appeal",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="appeal_end_date",
            field=models.DateField(
                blank=True,
                help_text="Verdict date of the Supreme Court appeal",
                null=True,
            ),
        ),
    ]
