from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    MCPServer,
    Prompt,
    Skill,
    Summary,
    Draft,
    DraftVersion,
    LLMProvider,
    PublicChatConfig,
    PROVIDERS_REQUIRING_API_KEY,
)


class CurrentUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]

    def get_role(self, obj):
        return "administrator" if obj.is_staff else "caseworker"


class MCPServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCPServer
        fields = [
            "id",
            "name",
            "display_name",
            "url",
            "auth_type",
            "auth_token",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
        extra_kwargs = {"auth_token": {"write_only": True}}


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "content",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "prompt",
            "skills",
            "model",
            "temperature",
            "max_tokens",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SummarySerializer(serializers.ModelSerializer):
    prompt_name = serializers.SerializerMethodField()

    class Meta:
        model = Summary
        fields = [
            "id",
            "case_number",
            "prompt",
            "prompt_name",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_prompt_name(self, obj):
        """Return prompt name or None if prompt is not set."""
        return obj.prompt.name if obj.prompt else None


class DraftVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DraftVersion
        fields = ["id", "content", "created_at"]
        read_only_fields = ["id", "created_at"]


class DraftSerializer(serializers.ModelSerializer):
    prompt_name = serializers.SerializerMethodField()
    versions = DraftVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Draft
        fields = [
            "id",
            "case_number",
            "prompt",
            "prompt_name",
            "content",
            "status",
            "external_reference_id",
            "versions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "external_reference_id",
            "versions",
            "created_at",
            "updated_at",
        ]

    def get_prompt_name(self, obj):
        """Return prompt name or None if prompt is not set."""
        return obj.prompt.name if obj.prompt else None


class LLMProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMProvider
        fields = [
            "id",
            "provider_type",
            "model",
            "api_key",
            "temperature",
            "max_tokens",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"api_key": {"write_only": True}}

    def validate(self, data):
        """Validate that api_key is provided for providers that require it."""
        provider_type = data.get(
            "provider_type", getattr(self.instance, "provider_type", None)
        )
        api_key = data.get("api_key", getattr(self.instance, "api_key", None))

        if provider_type in PROVIDERS_REQUIRING_API_KEY and not api_key:
            raise serializers.ValidationError(
                {"api_key": f"API key is required for {provider_type}"}
            )

        return data


class PublicChatConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicChatConfig
        fields = [
            "id",
            "name",
            "is_active",
            "enabled",
            "prompt",
            "llm_provider",
            "quota_scope",
            "quota_limit",
            "quota_window_seconds",
            "max_question_chars",
            "max_history_turns",
            "max_history_chars",
            "max_mcp_results",
            "max_tool_calls",
            "max_evidence_chars",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
