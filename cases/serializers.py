"""
Serializers for the Jawafdehi accountability platform API.

See: .kiro/specs/accountability-platform-core/design.md
"""

from rest_framework import serializers
from .models import Case, DocumentSource


class CaseSerializer(serializers.ModelSerializer):
    """
    Serializer for Case model.
    
    Exposes all fields except:
    - contributors (internal only)
    - state (internal workflow detail)
    - version (internal versioning detail)
    """
    
    class Meta:
        model = Case
        fields = [
            'id',
            'case_id',
            'case_type',
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


class DocumentSourceSerializer(serializers.ModelSerializer):
    """
    Serializer for DocumentSource model.
    
    Used for public API access to sources associated with published cases.
    """
    
    class Meta:
        model = DocumentSource
        fields = [
            'id',
            'source_id',
            'title',
            'description',
            'url',
            'related_entity_ids',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields  # API is read-only
