from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User

# Providers that require an API key for authentication
PROVIDERS_REQUIRING_API_KEY = ["openai", "anthropic", "google", "azure"]


class MCPServer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Custom name for reference (no spaces, use hyphens)",
    )
    url = models.URLField()
    auth_type = models.CharField(
        max_length=50,
        choices=[("bearer", "Bearer"), ("api_key", "API Key")],
    )
    # TODO: Replace with encrypted field or secret reference (e.g., django-encrypted-model-fields)
    # Storing secrets as plain text is a security risk
    auth_token = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("connected", "Connected"),
            ("disconnected", "Disconnected"),
            ("error", "Error"),
        ],
        default="disconnected",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]


class Skill(models.Model):
    """Reusable instruction block that can be attached to prompts."""

    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Human-friendly skill name",
    )
    description = models.TextField()
    content = models.TextField(
        help_text="Instruction content loaded into selected prompts"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.name

    class Meta:
        ordering = ["-created_at"]


class Prompt(models.Model):
    """Reusable prompt profile for LLM-backed features."""

    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Custom name for loading prompt profiles with /display_name syntax",
    )
    description = models.TextField()
    prompt = models.TextField()
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="prompts",
        help_text="Optional instruction blocks loaded with this prompt",
    )
    # Model should be set by application logic based on configured provider
    model = models.CharField(max_length=100)
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]


class Summary(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="cw_summaries"
    )
    case_number = models.CharField(max_length=100)
    prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.case_number} - {self.user.username}"

    class Meta:
        ordering = ["-created_at"]


class Draft(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("posted", "Posted"),
        ("archived", "Archived"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cw_drafts")
    case_number = models.CharField(max_length=100)
    prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    external_reference_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.case_number} - {self.user.username}"

    class Meta:
        ordering = ["-created_at"]


class DraftVersion(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="versions")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.draft.case_number} - v{self.id}"

    class Meta:
        ordering = ["-created_at"]


class LLMProvider(models.Model):
    PROVIDER_CHOICES = [
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic Claude"),
        ("google", "Google Gemini"),
        ("ollama", "Ollama (Local)"),
        ("azure", "Azure OpenAI"),
        ("custom", "Custom"),
    ]

    provider_type = models.CharField(
        max_length=50, choices=PROVIDER_CHOICES, unique=True
    )
    model = models.CharField(max_length=100)
    # TODO: Replace with encrypted field or secret reference (e.g., django-encrypted-model-fields)
    # Storing secrets as plain text is a security risk
    # Optional for local providers like ollama
    api_key = models.CharField(max_length=500, blank=True, null=True)
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=2000)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate that api_key is provided for providers that require it."""
        from django.core.exceptions import ValidationError

        if self.provider_type in PROVIDERS_REQUIRING_API_KEY and not self.api_key:
            raise ValidationError(
                f"API key is required for {self.get_provider_type_display()}"
            )

    def __str__(self):
        return f"{self.provider_type} - {self.model}"

    class Meta:
        ordering = ["-created_at"]


class PublicChatConfig(models.Model):
    """Admin-managed prompt, provider, quota, and context limits for public chat."""

    class QuotaScope(models.TextChoices):
        IP_SESSION = "ip_session", "IP + Session"
        SESSION = "session", "Session"
        IP = "ip", "IP"

    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    enabled = models.BooleanField(default=True)
    prompt = models.ForeignKey(
        Prompt,
        on_delete=models.PROTECT,
        related_name="public_chat_configs",
    )
    llm_provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="public_chat_configs",
        help_text="Optional provider override. Falls back to the active provider.",
    )
    quota_scope = models.CharField(
        max_length=20,
        choices=QuotaScope.choices,
        default=QuotaScope.IP_SESSION,
    )
    quota_limit = models.PositiveIntegerField(default=10)
    quota_window_seconds = models.PositiveIntegerField(default=86400)
    max_question_chars = models.PositiveIntegerField(default=1000)
    max_history_turns = models.PositiveIntegerField(default=6)
    max_history_chars = models.PositiveIntegerField(default=4000)
    max_mcp_results = models.PositiveIntegerField(default=5)
    max_tool_calls = models.PositiveIntegerField(default=3)
    max_evidence_chars = models.PositiveIntegerField(default=8000)
    knowledge_rag_enabled = models.BooleanField(default=False)
    knowledge_collections = models.ManyToManyField(
        "knowledge.KnowledgeCollection",
        blank=True,
        related_name="public_chat_configs",
        help_text="Public knowledge collections exposed to anonymous public chat.",
    )
    max_knowledge_results = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        errors = {}
        for field in [
            "quota_limit",
            "quota_window_seconds",
            "max_question_chars",
            "max_history_turns",
            "max_history_chars",
            "max_mcp_results",
            "max_tool_calls",
            "max_evidence_chars",
            "max_knowledge_results",
        ]:
            if getattr(self, field) < 1:
                errors[field] = "Must be at least 1."

        if self.is_active:
            queryset = PublicChatConfig.objects.filter(is_active=True)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            if queryset.exists():
                errors["is_active"] = "Only one public chat config can be active."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-is_active", "-created_at"]
