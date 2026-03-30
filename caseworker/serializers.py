from rest_framework import serializers
from django.contrib.auth.models import User
from .models import MCPServer, Skill, Summary, Draft, DraftVersion, LLMProvider


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
            "id", "name", "display_name", "url", "auth_type",
            "auth_token", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
        extra_kwargs = {"auth_token": {"write_only": True}}


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = [
            "id", "name", "display_name", "description", "prompt",
            "model", "temperature", "max_tokens", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SummarySerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)

    class Meta:
        model = Summary
        fields = ["id", "case_number", "skill", "skill_name", "content", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class DraftVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DraftVersion
        fields = ["id", "content", "created_at"]
        read_only_fields = ["id", "created_at"]


class DraftSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    versions = DraftVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Draft
        fields = [
            "id", "case_number", "skill", "skill_name", "content",
            "status", "external_reference_id", "versions", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "external_reference_id", "versions", "created_at", "updated_at"]


class LLMProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMProvider
        fields = [
            "id", "provider_type", "model", "api_key", "temperature",
            "max_tokens", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"api_key": {"write_only": True}}
