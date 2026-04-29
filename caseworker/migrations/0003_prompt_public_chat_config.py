from django.db import migrations, models
import django.db.models.deletion


def seed_public_chat_config(apps, schema_editor):
    Prompt = apps.get_model("caseworker", "Prompt")
    PublicChatConfig = apps.get_model("caseworker", "PublicChatConfig")

    prompt, _ = Prompt.objects.get_or_create(
        name="public-chat",
        defaults={
            "display_name": "Public Chat",
            "description": "Default public chat prompt for published Jawafdehi content.",
            "prompt": (
                "You are Jawafdehi's public chat assistant. Answer only from the "
                "provided public evidence. If the evidence is missing, private, "
                "or insufficient, say you cannot verify the answer yet. Do not "
                "invent facts, counts, cases, or sources."
            ),
            "model": "claude-opus-4-6",
            "temperature": 0.2,
            "max_tokens": 1000,
        },
    )

    if not PublicChatConfig.objects.exists():
        PublicChatConfig.objects.create(
            name="default",
            is_active=True,
            enabled=True,
            prompt=prompt,
            quota_scope="ip_session",
            quota_limit=10,
            quota_window_seconds=86400,
            max_question_chars=1000,
            max_history_turns=6,
            max_history_chars=4000,
            max_mcp_results=5,
            max_tool_calls=3,
            max_evidence_chars=8000,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        (
            "caseworker",
            "0002_alter_llmprovider_api_key_alter_mcpserver_auth_token_and_more",
        ),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Skill",
            new_name="Prompt",
        ),
        migrations.RenameField(
            model_name="summary",
            old_name="skill",
            new_name="prompt",
        ),
        migrations.RenameField(
            model_name="draft",
            old_name="skill",
            new_name="prompt",
        ),
        migrations.AlterField(
            model_name="prompt",
            name="display_name",
            field=models.CharField(
                blank=True,
                help_text="Custom name for loading prompt profiles with /display_name syntax",
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.CreateModel(
            name="Skill",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                (
                    "display_name",
                    models.CharField(
                        blank=True,
                        help_text="Human-friendly skill name",
                        max_length=255,
                        null=True,
                        unique=True,
                    ),
                ),
                ("description", models.TextField()),
                (
                    "content",
                    models.TextField(
                        help_text="Instruction content loaded into selected prompts"
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddField(
            model_name="prompt",
            name="skills",
            field=models.ManyToManyField(
                blank=True,
                help_text="Optional instruction blocks loaded with this prompt",
                related_name="prompts",
                to="caseworker.skill",
            ),
        ),
        migrations.CreateModel(
            name="PublicChatConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "quota_scope",
                    models.CharField(
                        choices=[
                            ("ip_session", "IP + Session"),
                            ("session", "Session"),
                            ("ip", "IP"),
                        ],
                        default="ip_session",
                        max_length=20,
                    ),
                ),
                ("quota_limit", models.PositiveIntegerField(default=10)),
                ("quota_window_seconds", models.PositiveIntegerField(default=86400)),
                ("max_question_chars", models.PositiveIntegerField(default=1000)),
                ("max_history_turns", models.PositiveIntegerField(default=6)),
                ("max_history_chars", models.PositiveIntegerField(default=4000)),
                ("max_mcp_results", models.PositiveIntegerField(default=5)),
                ("max_tool_calls", models.PositiveIntegerField(default=3)),
                ("max_evidence_chars", models.PositiveIntegerField(default=8000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "llm_provider",
                    models.ForeignKey(
                        blank=True,
                        help_text="Optional provider override. Falls back to the active provider.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="public_chat_configs",
                        to="caseworker.llmprovider",
                    ),
                ),
                (
                    "prompt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="public_chat_configs",
                        to="caseworker.prompt",
                    ),
                ),
            ],
            options={"ordering": ["-is_active", "-created_at"]},
        ),
        migrations.RunPython(seed_public_chat_config, noop_reverse),
    ]
