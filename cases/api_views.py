"""
API ViewSets for the Jawafdehi accountability platform.

See: .kiro/specs/accountability-platform-core/design.md
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Max
from django.db import connection
from .models import Case, CaseState, DocumentSource
from .serializers import CaseSerializer, DocumentSourceSerializer


class CaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only API for Cases.
    
    Provides:
    - List endpoint: GET /api/cases/
    - Retrieve endpoint: GET /api/cases/{id}/
    
    Filtering:
    - case_type: Filter by case type
    - tags: Filter by tags
    
    Search:
    - Full-text search across title, description, key_allegations
    
    Only published cases (state=PUBLISHED) with the highest version
    per case_id are accessible.
    """
    
    serializer_class = CaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['case_type']
    search_fields = ['title', 'description', 'key_allegations']
    
    def get_queryset(self):
        """
        Return only published cases with the highest version per case_id.
        
        Implementation:
        1. Filter to only PUBLISHED cases
        2. For each case_id, return only the highest version
        """
        # Get all published cases
        published_cases = Case.objects.filter(state=CaseState.PUBLISHED)
        
        # Find the highest version for each case_id
        # Group by case_id and get the max version
        highest_versions = published_cases.values('case_id').annotate(
            max_version=Max('version')
        )
        
        # Build a list of (case_id, version) tuples for filtering
        case_version_pairs = [
            (item['case_id'], item['max_version']) 
            for item in highest_versions
        ]
        
        # Filter to only include cases matching (case_id, version) pairs
        q_objects = Q()
        for case_id, version in case_version_pairs:
            q_objects |= Q(case_id=case_id, version=version)
        
        if q_objects:
            queryset = published_cases.filter(q_objects)
        else:
            queryset = published_cases.none()
        
        # Apply tag filtering if provided
        tags_param = self.request.query_params.get('tags', None)
        if tags_param:
            # Filter cases that contain the specified tag
            # For SQLite, we need to filter in Python since it doesn't support JSON contains
            # For PostgreSQL, we can use the contains lookup
            if connection.vendor == 'postgresql':
                queryset = queryset.filter(tags__contains=[tags_param])
            else:
                # For SQLite, filter by checking if tag is in the list
                # Get all case IDs that have the tag
                case_ids_with_tag = [
                    case.id for case in queryset 
                    if case.tags and tags_param in case.tags
                ]
                queryset = queryset.filter(id__in=case_ids_with_tag)
        
        return queryset.order_by('-created_at')


class DocumentSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only API for DocumentSources.
    
    Provides:
    - List endpoint: GET /api/sources/
    - Retrieve endpoint: GET /api/sources/{id}/
    
    Only sources associated with published cases are accessible.
    """
    
    serializer_class = DocumentSourceSerializer
    
    def get_queryset(self):
        """
        Return only sources associated with published cases.
        
        A source is accessible if its associated case is published.
        """
        # Get all sources where the associated case is published
        # and not soft-deleted
        return DocumentSource.objects.filter(
            case__state=CaseState.PUBLISHED,
            is_deleted=False
        ).distinct()
