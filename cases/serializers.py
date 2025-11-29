"""
Serializers for the Jawafdehi accountability platform API.

See: .kiro/specs/accountability-platform-core/design.md
"""

from rest_framework import serializers
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Case, DocumentSource, JawafEntity, CaseState


class JawafEntitySerializer(serializers.ModelSerializer):
    """
    Serializer for JawafEntity model.
    """
    
    class Meta:
        model = JawafEntity
        fields = ['id', 'nes_id', 'display_name']


class CaseSerializer(serializers.ModelSerializer):
    """
    Serializer for Case model.
    
    Exposes all fields except:
    - contributors (internal only)
    - version (internal versioning detail)
    
    The state field is always included to indicate case status (PUBLISHED or IN_REVIEW).
    """
    
    alleged_entities = JawafEntitySerializer(many=True, read_only=True)
    related_entities = JawafEntitySerializer(many=True, read_only=True)
    locations = JawafEntitySerializer(many=True, read_only=True)
    tags = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of tags for categorization (e.g., 'land-encroachment', 'national-interest')",
        required=False
    )
    key_allegations = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of key allegation statements",
        required=False
    )
    timeline = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of timeline entries with date, title, and description",
        required=False
    )
    evidence = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of evidence entries with source_id and description",
        required=False
    )
    versionInfo = serializers.JSONField(
        help_text="Version metadata tracking changes (version_number, user_id, change_summary, datetime)",
        required=False
    )
    
    class Meta:
        model = Case
        fields = [
            'id',
            'case_id',
            'case_type',
            'state',
            'title',
            'case_start_date',
            'case_end_date',
            'alleged_entities',
            'related_entities',
            'locations',
            'tags',
            'description',
            'key_allegations',
            'timeline',
            'evidence',
            'versionInfo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields  # API is read-only


class CaseDetailSerializer(CaseSerializer):
    """
    Serializer for Case detail view with audit history.
    
    Includes audit_history field containing versionInfo from all
    published versions with the same case_id.
    """
    audit_history = serializers.SerializerMethodField(
        help_text="Complete audit trail showing all published versions of this case"
    )
    
    class Meta(CaseSerializer.Meta):
        fields = CaseSerializer.Meta.fields + ['audit_history']
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_audit_history(self, obj):
        """
        Get versionInfo from all published versions with the same case_id.
        
        If EXPOSE_CASES_IN_REVIEW feature flag is enabled, also includes IN_REVIEW versions.
        
        Returns a list of versionInfo objects ordered by version (newest first).
        """
        # Get all published versions with the same case_id
        # (and in-review if feature flag is enabled)
        if settings.EXPOSE_CASES_IN_REVIEW:
            all_versions = Case.objects.filter(
                case_id=obj.case_id,
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            ).order_by('-version')
        else:
            all_versions = Case.objects.filter(
                case_id=obj.case_id,
                state=CaseState.PUBLISHED
            ).order_by('-version')
        
        # Extract versionInfo from each version
        audit_history = []
        for version in all_versions:
            if version.versionInfo:
                audit_history.append(version.versionInfo)
        
        return audit_history


class DocumentSourceSerializer(serializers.ModelSerializer):
    """
    Serializer for DocumentSource model.
    
    Used for public API access to sources associated with published cases.
    """
    
    related_entities = JawafEntitySerializer(many=True, read_only=True)
    
    class Meta:
        model = DocumentSource
        fields = [
            'id',
            'source_id',
            'title',
            'description',
            'url',
            'related_entities',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields  # API is read-only
