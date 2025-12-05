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
    alleged_cases = serializers.SerializerMethodField(
        help_text="List of case IDs where this entity is alleged"
    )
    related_cases = serializers.SerializerMethodField(
        help_text="List of case IDs where this entity is related or a location"
    )
    
    class Meta:
        model = JawafEntity
        fields = ['id', 'nes_id', 'display_name', 'alleged_cases', 'related_cases']
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_alleged_cases(self, obj):
        """
        Get list of case IDs where this entity is alleged.
        
        Only includes PUBLISHED cases (and IN_REVIEW if feature flag is enabled).
        """
        from django.conf import settings
        
        if settings.EXPOSE_CASES_IN_REVIEW:
            cases = obj.cases_as_alleged.filter(
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            )
        else:
            cases = obj.cases_as_alleged.filter(state=CaseState.PUBLISHED)
        
        return list(cases.values_list('id', flat=True))
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_related_cases(self, obj):
        """
        Get list of case IDs where this entity is related or a location.
        
        Only includes PUBLISHED cases (and IN_REVIEW if feature flag is enabled).
        Excludes cases where entity is already alleged (to avoid duplicates).
        """
        from django.conf import settings
        from django.db.models import Q
        
        # Get alleged case IDs to exclude
        if settings.EXPOSE_CASES_IN_REVIEW:
            alleged_case_ids = obj.cases_as_alleged.filter(
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            ).values_list('id', flat=True)
        else:
            alleged_case_ids = obj.cases_as_alleged.filter(
                state=CaseState.PUBLISHED
            ).values_list('id', flat=True)
        
        # Get related and location cases
        if settings.EXPOSE_CASES_IN_REVIEW:
            related_cases = obj.cases_as_related.filter(
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            ).exclude(id__in=alleged_case_ids)
            
            location_cases = obj.cases_as_location.filter(
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            ).exclude(id__in=alleged_case_ids)
        else:
            related_cases = obj.cases_as_related.filter(
                state=CaseState.PUBLISHED
            ).exclude(id__in=alleged_case_ids)
            
            location_cases = obj.cases_as_location.filter(
                state=CaseState.PUBLISHED
            ).exclude(id__in=alleged_case_ids)
        
        # Combine and deduplicate
        case_ids = set(related_cases.values_list('id', flat=True))
        case_ids.update(location_cases.values_list('id', flat=True))
        
        return list(case_ids)


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
