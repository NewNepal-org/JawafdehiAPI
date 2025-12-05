"""
API ViewSets for the Jawafdehi accountability platform.

See: .kiro/specs/accountability-platform-core/design.md
"""

from rest_framework import viewsets, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Max
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import Case, CaseState, DocumentSource, JawafEntity
from .serializers import CaseSerializer, CaseDetailSerializer, DocumentSourceSerializer, JawafEntitySerializer


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
        
        If EXPOSE_CASES_IN_REVIEW feature flag is enabled, also includes IN_REVIEW cases.
        
        Implementation:
        1. Filter to PUBLISHED cases (and IN_REVIEW if flag is enabled)
        2. For each case_id, return only the highest version
        """
        # Get all published cases (and in-review if feature flag is enabled)
        if settings.EXPOSE_CASES_IN_REVIEW:
            published_cases = Case.objects.filter(
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            )
        else:
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
        Return only sources referenced in evidence of published cases.
        
        If EXPOSE_CASES_IN_REVIEW feature flag is enabled, also includes sources
        from IN_REVIEW cases.
        
        A source is accessible if it's referenced in the evidence field
        of at least one published case (or in-review case if flag is enabled).
        """
        # Get all published cases (and in-review if feature flag is enabled)
        if settings.EXPOSE_CASES_IN_REVIEW:
            published_cases = Case.objects.filter(
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            )
        else:
            published_cases = Case.objects.filter(state=CaseState.PUBLISHED)
        
        # Extract all source_ids from evidence fields
        source_ids = set()
        for case in published_cases:
            if case.evidence:
                for evidence_item in case.evidence:
                    if isinstance(evidence_item, dict) and 'source_id' in evidence_item:
                        source_ids.add(evidence_item['source_id'])
        
        # Return sources that are referenced and not soft-deleted
        return DocumentSource.objects.filter(
            source_id__in=source_ids,
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


@extend_schema_view(
    list=extend_schema(
        summary="List all entities",
        description="""
        Retrieve a paginated list of all entities in the system.
        
        Entities can have either:
        - `nes_id`: Reference to Nepal Entity Service
        - `display_name`: Custom entity name
        - Both fields (display_name is optional when nes_id is present)
        
        **Search:**
        - `search`: Search across nes_id and display_name
        
        **Pagination:**
        - Results are paginated with 50 items per page
        - Use `page` parameter to navigate pages
        """,
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search across nes_id and display_name',
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
        tags=['entities'],
    ),
    retrieve=extend_schema(
        summary="Retrieve an entity",
        description="""
        Retrieve detailed information about a specific entity.
        
        Returns entity with id, nes_id, and display_name.
        """,
        tags=['entities'],
    ),
)
class JawafEntityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only API for JawafEntities.
    
    Provides:
    - List endpoint: GET /api/entities/ (filtered by case association)
    - Retrieve endpoint: GET /api/entities/{id}/
    
    Search:
    - Full-text search across nes_id and display_name
    
    Only entities associated with published cases are returned in list view.
    Entities must appear in alleged_entities or related_entities (not locations).
    """
    
    serializer_class = JawafEntitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nes_id', 'display_name']
    
    def get_queryset(self):
        """
        Return entities based on action.
        
        For list action: Only entities that appear in published cases.
        For retrieve action: All entities (no filtering).
        
        An entity is included in list if it appears in alleged_entities or 
        related_entities of at least one published case.
        
        Note: Location entities are excluded from the list.
        
        If EXPOSE_CASES_IN_REVIEW feature flag is enabled, also includes
        entities from IN_REVIEW cases.
        
        Uses caching to avoid expensive queryset evaluation.
        """
        # For retrieve action, return all entities
        if self.action == 'retrieve':
            return JawafEntity.objects.all()
        
        # For list action, filter by case association
        from django.core.cache import cache
        
        # Try to get entity IDs from cache
        entity_ids = cache.get('public_entities_list')
        
        if entity_ids is None:
            # Cache miss - compute entity IDs
            if settings.EXPOSE_CASES_IN_REVIEW:
                published_cases = Case.objects.filter(
                    state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
                )
            else:
                published_cases = Case.objects.filter(state=CaseState.PUBLISHED)
            
            entity_ids = set()
            for case in published_cases:
                # Add alleged entities
                entity_ids.update(case.alleged_entities.values_list('id', flat=True))
                # Add related entities
                entity_ids.update(case.related_entities.values_list('id', flat=True))
            
            # Cache for 10 minutes - stale cache is acceptable
            cache.set('public_entities_list', entity_ids, timeout=600)
        
        return JawafEntity.objects.filter(id__in=entity_ids).order_by('-created_at')



@extend_schema(
    summary="Get case statistics",
    description="""
    Retrieve aggregate statistics about cases in the system.
    
    Returns:
    - `published_cases`: Number of cases with state PUBLISHED
    - `cases_under_investigation`: Number of cases with state DRAFT or IN_REVIEW
    - `cases_closed`: Number of cases with state CLOSED
    - `entities_tracked`: Number of unique entities involved in published cases
    - `last_updated`: Timestamp when statistics were last calculated
    
    **Caching:**
    - Statistics are cached for 5 minutes to optimize performance
    - The cache is automatically refreshed after expiration
    """,
    tags=['statistics'],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'published_cases': {'type': 'integer', 'example': 127},
                'cases_under_investigation': {'type': 'integer', 'example': 43},
                'cases_closed': {'type': 'integer', 'example': 31},
                'entities_tracked': {'type': 'integer', 'example': 89},
                'last_updated': {'type': 'string', 'format': 'date-time', 'example': '2024-12-04T10:30:00Z'},
            }
        }
    }
)
class StatisticsView(APIView):
    """
    Public API endpoint for case statistics.
    
    Provides aggregate counts of cases by state and unique entities tracked.
    Results are cached for 5 minutes using LocMemCache.
    """
    
    def get(self, request):
        """
        Get cached or calculate fresh statistics.
        """
        cache_key = 'stats-cache'
        
        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        # Calculate statistics
        stats = {
            'published_cases': Case.objects.filter(state=CaseState.PUBLISHED).count(),
            'cases_under_investigation': Case.objects.filter(
                state__in=[CaseState.DRAFT, CaseState.IN_REVIEW]
            ).count(),
            'cases_closed': Case.objects.filter(state=CaseState.CLOSED).count(),
            'entities_tracked': JawafEntity.objects.count(),
            'last_updated': timezone.now().isoformat(),
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, stats, timeout=300)
        
        return Response(stats)
