"""
API ViewSets for the Jawafdehi accountability platform.

See: .kiro/specs/accountability-platform-core/design.md
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Max
from django.db import connection
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import Case, CaseState, DocumentSource
from .serializers import CaseSerializer, CaseDetailSerializer, DocumentSourceSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List published cases",
        description="""
        Retrieve a paginated list of published accountability cases.
        
        Only cases with state=PUBLISHED and the highest version per case_id are returned.
        Results are ordered by creation date (newest first).
        
        **Filtering:**
        - `case_type`: Filter by case type (CORRUPTION or PROMISES)
        - `tags`: Filter cases containing a specific tag
        
        **Search:**
        - `search`: Full-text search across title, description, and key allegations
        
        **Pagination:**
        - Results are paginated with 20 items per page
        - Use `page` parameter to navigate pages
        """,
        parameters=[
            OpenApiParameter(
                name='case_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by case type',
                enum=['CORRUPTION', 'PROMISES'],
                required=False,
            ),
            OpenApiParameter(
                name='tags',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter cases containing this tag',
                required=False,
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search across title, description, and key allegations',
                required=False,
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination',
                required=False,
            ),
        ],
        tags=['cases'],
    ),
    retrieve=extend_schema(
        summary="Retrieve a case with audit history",
        description="""
        Retrieve detailed information about a specific published case.
        
        This endpoint includes:
        - Complete case data (title, description, allegations, evidence, timeline)
        - Audit history showing all published versions of this case
        
        Only published cases are accessible through this endpoint.
        """,
        tags=['cases'],
    ),
)
class CaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only API for Cases.
    
    Provides:
    - List endpoint: GET /api/cases/
    - Retrieve endpoint: GET /api/cases/{id}/ (includes audit history)
    
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
    
    def get_serializer_class(self):
        """
        Use CaseDetailSerializer for retrieve action to include audit history.
        """
        if self.action == 'retrieve':
            return CaseDetailSerializer
        return CaseSerializer
    
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


@extend_schema_view(
    list=extend_schema(
        summary="List document sources",
        description="""
        Retrieve a paginated list of document sources.
        
        Only sources associated with published cases are accessible.
        Soft-deleted sources (is_deleted=True) are excluded.
        
        **Pagination:**
        - Results are paginated with 20 items per page
        - Use `page` parameter to navigate pages
        """,
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination',
                required=False,
            ),
        ],
        tags=['sources'],
    ),
    retrieve=extend_schema(
        summary="Retrieve a document source",
        description="""
        Retrieve detailed information about a specific document source.
        
        The endpoint accepts either the database id (numeric) or the source_id 
        (e.g., 'source:20240115:abc123').
        
        Only sources associated with at least one published case are accessible.
        """,
        tags=['sources'],
    ),
)
class DocumentSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only API for DocumentSources.
    
    Provides:
    - List endpoint: GET /api/sources/
    - Retrieve endpoint: GET /api/sources/{id_or_source_id}/
    
    The retrieve endpoint accepts either the database id or the source_id.
    Only sources associated with published cases are accessible.
    """
    
    serializer_class = DocumentSourceSerializer
    lookup_field = 'pk'
    
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
    
    def get_object(self):
        """
        Override to support lookup by either id or source_id.
        
        Tries to lookup by id first (if numeric), then falls back to source_id.
        """
        queryset = self.filter_queryset(self.get_queryset())
        lookup_value = self.kwargs.get(self.lookup_field)
        
        # Try to lookup by id if the value is numeric
        if lookup_value.isdigit():
            try:
                obj = queryset.get(id=int(lookup_value))
                self.check_object_permissions(self.request, obj)
                return obj
            except DocumentSource.DoesNotExist:
                pass
        
        # Fall back to lookup by source_id
        try:
            obj = queryset.get(source_id=lookup_value)
            self.check_object_permissions(self.request, obj)
            return obj
        except DocumentSource.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(f"Source with id or source_id '{lookup_value}' not found.")
