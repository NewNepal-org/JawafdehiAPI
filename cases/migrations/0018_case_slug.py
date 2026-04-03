from django.core.validators import RegexValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0017_feedback_attachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="case",
            name="slug",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text=(
                    "A slug will go in the URL. For CIAA corruption cases, you can prepend the "
                    "special court case number (e.g. case-case-078-WC-0123-sunil-poudel)."
                ),
                max_length=50,
                null=True,
                unique=True,
                validators=[
                    RegexValidator(
                        regex=r"^(?!\d)[A-Za-z0-9-]{1,50}$",
                        message=(
                            "Slug must be 1-50 characters, can only use letters, numbers, and '-', "
                            "and cannot start with a digit."
                        ),
                    )
                ],
            ),
        ),
    ]
