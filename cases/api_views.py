"""
API ViewSets for the Jawafdehi accountability platform.

See: .kiro/specs/accountability-platform-core/design.md
"""

from django.core.cache import cache
from django.db import connection, transaction, IntegrityError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
import jsonpatch

from .admin import CaseAdminForm
from .caseworker_serializers import (
    BLOCKED_PATH_PREFIXES,
    CaseCreateSerializer,
    CasePatchSerializer,
)
from .models import (
    Case,
    CaseState,
    DocumentSource,
    JawafEntity,
    CaseEntityRelationship,
    RelationshipType,
)
from .rules.predicates import can_change_case
from .serializers import (
    CaseDetailSerializer,
    CaseSerializer,
    DocumentSourceSerializer,
    FeedbackSerializer,
    JawafEntitySerializer,
    CaseEntityRelationshipSerializer,
)


@extend_schema_view(
    create=extend_schema(
        summary="Create a draft case",
        description="""
        Create a new case through the same validation rules used by the Django admin form.

        Authenticated users create cases in `DRAFT` state only. The request user is
        automatically added as a contributor on the new case.
        """,
        request=CaseCreateSerializer,
        responses={201: CaseSerializer},
        tags=["cases"],
    ),
    list=extend_schema(
        summary="List published cases",
        description="""
        Retrieve a paginated list of published accountability cases.
        
        Only cases with state=PUBLISHED are returned.
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
                name="case_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by case type",
                enum=["CORRUPTION", "PROMISES"],
                required=False,
            ),
            OpenApiParameter(
                name="tags",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter cases containing this tag",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search across title, description, and key allegations",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination",
                required=False,
            ),
        ],
        tags=["cases"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a case",
        description="""
        Retrieve detailed information about a specific published case.
        
        This endpoint includes complete case data (title, description, allegations,
        evidence, timeline) and any internal notes.
        
        Published and IN_REVIEW cases are accessible through this endpoint.
        """,
        tags=["cases"],
    ),
)
class CaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only API for Cases (with PATCH support for authenticated users).

    Provides:
    - Create endpoint: POST /api/cases/ (authenticated users only)
    - List endpoint: GET /api/cases/
    - Retrieve endpoint: GET /api/cases/{id}/
    - Patch endpoint: PATCH /api/cases/{id}/ (authenticated users only)

    Filtering:
    - case_type: Filter by case type
    - tags: Filter by tags

    Search:
    - Full-text search across title, description, key_allegations

    Only published cases (state=PUBLISHED) are accessible.
    The detail endpoint also includes IN_REVIEW cases.
    """

    serializer_class = CaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["case_type"]
    search_fields = ["title", "description", "key_allegations"]
    authentication_classes = [TokenAuthentication]

    def get_permissions(self):
        """
        Allow POST/PATCH for authenticated users, read-only for everyone else.
        """
        if self.action in {"create", "partial_update"}:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return CaseCreateSerializer
        if self.action == "retrieve":
            return CaseDetailSerializer
        return CaseSerializer

    def get_queryset(self):
        """
        Return cases filtered by state.

        List endpoint: PUBLISHED cases only.
        Retrieve endpoint: PUBLISHED and IN_REVIEW cases.
        Partial update endpoint: all cases (permission check happens in partial_update).
        """
        if self.action == "partial_update":
            # PATCH endpoint: return all cases, permission check happens in partial_update method
            return Case.objects.all()

        if self.action == "retrieve":
            queryset = Case.objects.filter(
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            )
        else:
            # List endpoint: only published cases
            queryset = Case.objects.filter(state=CaseState.PUBLISHED)

        # Apply tag filtering if provided
        tags_param = self.request.query_params.get("tags", None)
        if tags_param:
            # Filter cases that contain the specified tag
            # For SQLite, we need to filter in Python since it doesn't support JSON contains
            # For PostgreSQL, we can use the contains lookup
            if connection.vendor == "postgresql":
                queryset = queryset.filter(tags__contains=[tags_param])
            else:
                # For SQLite, filter by checking if tag is in the list
                # Get all case IDs that have the tag
                case_ids_with_tag = [
                    case.id
                    for case in queryset
                    if case.tags and tags_param in case.tags
                ]
                queryset = queryset.filter(id__in=case_ids_with_tag)

        return queryset.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        """
        POST /api/cases/

        Create a new case by delegating validation to the existing Django admin form
        so API and admin creation semantics stay aligned.
        """
        # Validate that request body is a JSON object (dict), not array or scalar
        if not isinstance(request.data, dict):
            return Response(
                {"detail": "Request body must be a JSON object."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        allowed_fields = set(CaseCreateSerializer().fields.keys())
        unexpected_fields = sorted(set(request.data.keys()) - allowed_fields)
        if unexpected_fields:
            return Response(
                {field: ["This field is not allowed."] for field in unexpected_fields},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        serializer = CaseCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        form = CaseAdminForm(data=serializer.validated_data, request=request)
        form.fields["case_id"].required = False
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        with transaction.atomic():
            case = form.save()
            case.contributors.add(request.user)

        return Response(CaseSerializer(case).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """
        PATCH /api/cases/{id}/

        Accepts an RFC 6902 JSON Patch document and applies it against a writable
        snapshot of the case. The snapshot is validated after patching, then scalar
        fields are saved via a bulk UPDATE and M2M relations are updated with .set().

        Blocked paths (id, case_id, version, state, contributors, timestamps,
        versionInfo) are rejected before the patch is applied.
        """
        try:
            case = self.get_object()
        except Case.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not can_change_case(request.user, case):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )

        patch_ops = request.data
        if not isinstance(patch_ops, list):
            return Response(
                {"detail": "Request body must be a JSON array of patch operations."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reject blocked paths before applying the patch
        for op in patch_ops:
            if not isinstance(op, dict):
                return Response(
                    {"detail": "Each patch operation must be a JSON object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            path = op.get("path", "")
            for blocked in BLOCKED_PATH_PREFIXES:
                if path == blocked or path.startswith(blocked + "/"):
                    return Response(
                        {"detail": f"Patching path '{path}' is not allowed."},
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    )

        snapshot = self._build_snapshot(case)
        try:
            patched = jsonpatch.apply_patch(snapshot, patch_ops)
        except (jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CasePatchSerializer(data=patched)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        validated = serializer.validated_data

        # Fields that map directly to Case model columns (updated via bulk UPDATE)
        scalar_fields = frozenset(
            [
                "title",
                "short_description",
                "description",
                "thumbnail_url",
                "banner_url",
                "case_start_date",
                "case_end_date",
                "tags",
                "key_allegations",
                "timeline",
                "evidence",
            ]
        )

        # Maps writable snapshot key → Case M2M attribute name
        m2m_fields = {
            "alleged_entity_ids": "alleged_entities",
            "related_entity_ids": "related_entities",
            "location_ids": "locations",
        }

        # Persist scalar field changes
        scalar_updates = {
            field: validated[field] for field in scalar_fields if field in validated
        }
        if scalar_updates:
            Case.objects.filter(pk=pk).update(**scalar_updates)

        # Persist M2M changes
        case.refresh_from_db()
        for id_field, m2m_attr in m2m_fields.items():
            if id_field in validated:
                getattr(case, m2m_attr).set(validated[id_field])

        case.refresh_from_db()
        return Response(CaseSerializer(case).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Get case entity relationships",
        description="""
        Retrieve all entity relationships for a specific case with optional filtering.
        
        **Filtering:**
        - `relationship_type`: Filter by relationship type (alleged, related, witness, opposition, victim)
        - Multiple types can be specified as comma-separated values
        
        **Response includes:**
        - Entity details (id, display_name, nes_id)
        - Relationship metadata (type, notes, created_at)
        - Aggregated counts by relationship type
        """,
        parameters=[
            OpenApiParameter(
                name="relationship_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by relationship type(s). Multiple types can be comma-separated.",
                required=False,
                examples=[
                    OpenApiExample("Single type", value="alleged"),
                    OpenApiExample("Multiple types", value="alleged,related"),
                    OpenApiExample(
                        "All types", value="alleged,related,witness,opposition,victim"
                    ),
                ],
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "relationships": {
                        "type": "array",
                        "items": {
                            "$ref": "#/components/schemas/CaseEntityRelationship"
                        },
                    },
                    "counts": {
                        "type": "object",
                        "properties": {
                            "alleged": {"type": "integer"},
                            "related": {"type": "integer"},
                            "witness": {"type": "integer"},
                            "opposition": {"type": "integer"},
                            "victim": {"type": "integer"},
                            "total": {"type": "integer"},
                        },
                    },
                },
            }
        },
        tags=["cases"],
    )
    @action(detail=True, methods=["get"], url_path="entities")
    def get_entities(self, request, pk=None):
        """
        GET /api/cases/{id}/entities/

        Get all entity relationships for a case with optional filtering by relationship type.
        Includes aggregated counts by relationship type.
        """
        case = self.get_object()

        # Get base queryset of relationships for this case
        relationships_qs = case.entity_relationships.select_related("entity").all()

        # Apply relationship_type filtering if provided
        relationship_type_param = request.query_params.get("relationship_type")
        if relationship_type_param:
            # Support comma-separated multiple types
            requested_types = [t.strip() for t in relationship_type_param.split(",")]

            # Validate relationship types
            valid_types = [choice[0] for choice in RelationshipType.choices]
            invalid_types = [t for t in requested_types if t not in valid_types]
            if invalid_types:
                return Response(
                    {
                        "error": f"Invalid relationship type(s): {', '.join(invalid_types)}",
                        "valid_types": valid_types,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            relationships_qs = relationships_qs.filter(
                relationship_type__in=requested_types
            )

        # Serialize the filtered relationships
        relationships_data = CaseEntityRelationshipSerializer(
            relationships_qs, many=True
        ).data

        # Calculate aggregated counts by relationship type for the entire case
        # (not just filtered results - this gives full context)
        all_relationships = case.entity_relationships.all()
        counts = {
            "alleged": all_relationships.filter(
                relationship_type=RelationshipType.ALLEGED
            ).count(),
            "related": all_relationships.filter(
                relationship_type=RelationshipType.RELATED
            ).count(),
            "witness": all_relationships.filter(
                relationship_type=RelationshipType.WITNESS
            ).count(),
            "opposition": all_relationships.filter(
                relationship_type=RelationshipType.OPPOSITION
            ).count(),
            "victim": all_relationships.filter(
                relationship_type=RelationshipType.VICTIM
            ).count(),
        }
        counts["total"] = sum(counts.values())

        return Response({"relationships": relationships_data, "counts": counts})

    @extend_schema(
        summary="Add entity relationship to case",
        description="""
        Add a new entity relationship to a case.
        
        **Required fields:**
        - `entity`: Entity ID to relate to the case
        - `relationship_type`: Type of relationship (alleged, related, witness, opposition, victim)
        
        **Optional fields:**
        - `notes`: Additional context about the relationship
        
        **Authentication required.**
        """,
        request=CaseEntityRelationshipSerializer,
        responses={
            201: CaseEntityRelationshipSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            409: OpenApiTypes.OBJECT,
        },
        tags=["cases"],
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="entities",
        permission_classes=[IsAuthenticated],
    )
    def add_entity(self, request, pk=None):
        """
        POST /api/cases/{id}/entities/

        Add a new entity relationship to a case.
        Requires authentication and case edit permissions.
        """
        case = self.get_object()

        # Check permissions
        if not can_change_case(request.user, case):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )

        # Validate request data
        serializer = CaseEntityRelationshipSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create the relationship
            relationship = CaseEntityRelationship.objects.create(
                case=case,
                entity_id=serializer.validated_data["entity"].id,
                relationship_type=serializer.validated_data["relationship_type"],
                notes=serializer.validated_data.get("notes", ""),
            )

            return Response(
                CaseEntityRelationshipSerializer(relationship).data,
                status=status.HTTP_201_CREATED,
            )

        except IntegrityError as e:
            # Handle unique constraint violations
            if "unique_case_entity_relationship_type" in str(e):
                return Response(
                    {
                        "detail": "This entity already has this relationship type with the case.",
                        "error_code": "duplicate_relationship",
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            raise

    @extend_schema(
        summary="Update entity relationship",
        description="""
        Update an existing entity relationship for a case.
        
        **Updatable fields:**
        - `relationship_type`: Change the relationship type
        - `notes`: Update relationship notes
        
        **Authentication required.**
        """,
        request=CaseEntityRelationshipSerializer,
        responses={
            200: CaseEntityRelationshipSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        tags=["cases"],
    )
    @action(
        detail=True,
        methods=["put"],
        url_path="entities/(?P<relationship_id>[^/.]+)",
        permission_classes=[IsAuthenticated],
    )
    def update_entity_relationship(self, request, pk=None, relationship_id=None):
        """
        PUT /api/cases/{id}/entities/{relationship_id}/

        Update an existing entity relationship.
        Requires authentication and case edit permissions.
        """
        case = self.get_object()

        # Check permissions
        if not can_change_case(request.user, case):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )

        # Get the relationship
        try:
            relationship = case.entity_relationships.get(id=relationship_id)
        except CaseEntityRelationship.DoesNotExist:
            return Response(
                {"detail": "Relationship not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Validate and update
        serializer = CaseEntityRelationshipSerializer(
            relationship, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            return Response(serializer.data)

        except IntegrityError as e:
            # Handle unique constraint violations
            if "unique_case_entity_relationship_type" in str(e):
                return Response(
                    {
                        "detail": "This entity already has this relationship type with the case.",
                        "error_code": "duplicate_relationship",
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            raise

    @extend_schema(
        summary="Remove entity relationship",
        description="""
        Remove an entity relationship from a case.
        
        **Authentication required.**
        """,
        responses={
            204: None,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        tags=["cases"],
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path="entities/(?P<relationship_id>[^/.]+)",
        permission_classes=[IsAuthenticated],
    )
    def remove_entity_relationship(self, request, pk=None, relationship_id=None):
        """
        DELETE /api/cases/{id}/entities/{relationship_id}/

        Remove an entity relationship from a case.
        Requires authentication and case edit permissions.
        """
        case = self.get_object()

        # Check permissions
        if not can_change_case(request.user, case):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )

        # Get and delete the relationship
        try:
            relationship = case.entity_relationships.get(id=relationship_id)
            relationship.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except CaseEntityRelationship.DoesNotExist:
            return Response(
                {"detail": "Relationship not found."}, status=status.HTTP_404_NOT_FOUND
            )

    def _build_snapshot(self, case: Case) -> dict:
        """Return a writable dict representing the patchable surface of a case."""
        return {
            "title": case.title,
            "short_description": case.short_description,
            "description": case.description,
            "thumbnail_url": case.thumbnail_url,
            "banner_url": case.banner_url,
            "case_start_date": (
                str(case.case_start_date) if case.case_start_date else None
            ),
            "case_end_date": str(case.case_end_date) if case.case_end_date else None,
            "case_type": case.case_type,
            "tags": list(case.tags) if case.tags else [],
            "key_allegations": (
                list(case.key_allegations) if case.key_allegations else []
            ),
            "timeline": list(case.timeline) if case.timeline else [],
            "evidence": list(case.evidence) if case.evidence else [],
            "alleged_entity_ids": list(
                case.alleged_entities.values_list("id", flat=True)
            ),
            "related_entity_ids": list(
                case.related_entities.values_list("id", flat=True)
            ),
            "location_ids": list(case.locations.values_list("id", flat=True)),
        }


@extend_schema_view(
    list=extend_schema(
        summary="List document sources",
        description="""
        Retrieve a paginated list of document sources.
        
        Only sources associated with published or in-review cases are accessible.
        Soft-deleted sources (is_deleted=True) are excluded.
        
        **Pagination:**
        - Results are paginated with 20 items per page
        - Use `page` parameter to navigate pages
        """,
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination",
                required=False,
            ),
        ],
        tags=["sources"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a document source",
        description="""
        Retrieve detailed information about a specific document source.
        
        The endpoint accepts either the database id (numeric) or the source_id 
        (e.g., 'source:20240115:abc123').
        
        Only sources associated with at least one published or in-review case are accessible.
        """,
        tags=["sources"],
    ),
)
class DocumentSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only API for DocumentSources.

    Provides:
    - List endpoint: GET /api/sources/
    - Retrieve endpoint: GET /api/sources/{id_or_source_id}/

    The retrieve endpoint accepts either the database id or the source_id.
    Only sources associated with published or in-review cases are accessible.
    """

    serializer_class = DocumentSourceSerializer
    lookup_field = "pk"

    def get_queryset(self):
        """
        Return only sources referenced in evidence of published or in-review cases.

        A source is accessible if it's referenced in the evidence field
        of at least one published or in-review case.
        """
        allowed_states = [CaseState.PUBLISHED, CaseState.IN_REVIEW]
        visible_cases = Case.objects.filter(state__in=allowed_states)

        # Extract all source_ids from evidence fields
        source_ids = set()
        for case in visible_cases:
            if case.evidence:
                for evidence_item in case.evidence:
                    if isinstance(evidence_item, dict) and "source_id" in evidence_item:
                        source_ids.add(evidence_item["source_id"])

        # Return sources that are referenced and not soft-deleted
        return DocumentSource.objects.filter(
            source_id__in=source_ids, is_deleted=False
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
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search across nes_id and display_name",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination",
                required=False,
            ),
        ],
        tags=["entities"],
    ),
    retrieve=extend_schema(
        summary="Retrieve an entity",
        description="""
        Retrieve detailed information about a specific entity.
        
        Returns entity with id, nes_id, and display_name.
        """,
        tags=["entities"],
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
    search_fields = ["nes_id", "display_name"]

    def get_queryset(self):
        """
        Return entities based on action.

        For list action: Only entities that appear in published cases.
        For retrieve action: All entities (no filtering).

        An entity is included in list if it appears in alleged_entities or
        related_entities of at least one published case.

        Note: Location entities are excluded from the list.

        Uses caching to avoid expensive queryset evaluation.
        """
        # For retrieve action, return all entities
        if self.action == "retrieve":
            return JawafEntity.objects.all()

        # For list action, filter by case association
        from django.core.cache import cache

        # Try to get entity IDs from cache
        entity_ids = cache.get("public_entities_list")

        if entity_ids is None:
            # Cache miss - compute entity IDs
            published_cases = Case.objects.filter(state=CaseState.PUBLISHED)

            entity_ids = set()
            for case in published_cases:
                # Add all entities from unified entities format
                entity_ids.update(case.unified_entities.values_list("id", flat=True))

            # Cache for 10 minutes - stale cache is acceptable
            cache.set("public_entities_list", entity_ids, timeout=600)

        return JawafEntity.objects.filter(id__in=entity_ids).order_by("-created_at")

    @extend_schema(
        summary="Get entity relationships across cases",
        description="""
        Retrieve all case relationships for a specific entity with optional filtering.
        
        **Filtering:**
        - `relationship_type`: Filter by relationship type (alleged, related, witness, opposition, victim)
        - `case_state`: Filter by case state (PUBLISHED, IN_REVIEW, DRAFT, CLOSED)
        - Multiple types can be specified as comma-separated values
        
        **Response includes:**
        - Case details (id, case_id, title, state)
        - Relationship metadata (type, notes, created_at)
        - Aggregated counts by relationship type
        """,
        parameters=[
            OpenApiParameter(
                name="relationship_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by relationship type(s). Multiple types can be comma-separated.",
                required=False,
                examples=[
                    OpenApiExample("Single type", value="alleged"),
                    OpenApiExample("Multiple types", value="alleged,related"),
                ],
            ),
            OpenApiParameter(
                name="case_state",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by case state(s). Multiple states can be comma-separated.",
                required=False,
                examples=[
                    OpenApiExample("Published only", value="PUBLISHED"),
                    OpenApiExample(
                        "Published and In Review", value="PUBLISHED,IN_REVIEW"
                    ),
                ],
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "entity": {"$ref": "#/components/schemas/JawafEntity"},
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "case": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "case_id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "state": {"type": "string"},
                                    },
                                },
                                "relationship_type": {"type": "string"},
                                "notes": {"type": "string"},
                                "created_at": {"type": "string", "format": "date-time"},
                            },
                        },
                    },
                    "counts": {
                        "type": "object",
                        "properties": {
                            "alleged": {"type": "integer"},
                            "related": {"type": "integer"},
                            "witness": {"type": "integer"},
                            "opposition": {"type": "integer"},
                            "victim": {"type": "integer"},
                            "total": {"type": "integer"},
                        },
                    },
                },
            }
        },
        tags=["entities"],
    )
    @action(detail=True, methods=["get"], url_path="relationships")
    def get_relationships(self, request, pk=None):
        """
        GET /api/entities/{id}/relationships/

        Get all case relationships for an entity with optional filtering.
        Includes aggregated counts by relationship type.
        """
        entity = self.get_object()

        # Get base queryset of relationships for this entity
        relationships_qs = entity.case_relationships.select_related("case").all()

        # Apply case_state filtering if provided (default to published cases only for public API)
        case_state_param = request.query_params.get("case_state", "PUBLISHED")
        if case_state_param:
            # Support comma-separated multiple states
            requested_states = [s.strip() for s in case_state_param.split(",")]

            # Validate case states
            valid_states = [choice[0] for choice in CaseState.choices]
            invalid_states = [s for s in requested_states if s not in valid_states]
            if invalid_states:
                return Response(
                    {
                        "error": f"Invalid case state(s): {', '.join(invalid_states)}",
                        "valid_states": valid_states,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            relationships_qs = relationships_qs.filter(case__state__in=requested_states)

        # Apply relationship_type filtering if provided
        relationship_type_param = request.query_params.get("relationship_type")
        if relationship_type_param:
            # Support comma-separated multiple types
            requested_types = [t.strip() for t in relationship_type_param.split(",")]

            # Validate relationship types
            valid_types = [choice[0] for choice in RelationshipType.choices]
            invalid_types = [t for t in requested_types if t not in valid_types]
            if invalid_types:
                return Response(
                    {
                        "error": f"Invalid relationship type(s): {', '.join(invalid_types)}",
                        "valid_types": valid_types,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            relationships_qs = relationships_qs.filter(
                relationship_type__in=requested_types
            )

        # Serialize the filtered relationships with case details
        relationships_data = []
        for rel in relationships_qs:
            relationships_data.append(
                {
                    "id": rel.id,
                    "case": {
                        "id": rel.case.id,
                        "case_id": rel.case.case_id,
                        "title": rel.case.title,
                        "state": rel.case.state,
                    },
                    "relationship_type": rel.relationship_type,
                    "notes": rel.notes,
                    "created_at": rel.created_at,
                }
            )

        # Calculate aggregated counts by relationship type for the entire entity
        # (not just filtered results - this gives full context)
        all_relationships = entity.case_relationships.filter(
            case__state__in=["PUBLISHED", "IN_REVIEW"]
        )
        counts = {
            "alleged": all_relationships.filter(
                relationship_type=RelationshipType.ALLEGED
            ).count(),
            "related": all_relationships.filter(
                relationship_type=RelationshipType.RELATED
            ).count(),
            "witness": all_relationships.filter(
                relationship_type=RelationshipType.WITNESS
            ).count(),
            "opposition": all_relationships.filter(
                relationship_type=RelationshipType.OPPOSITION
            ).count(),
            "victim": all_relationships.filter(
                relationship_type=RelationshipType.VICTIM
            ).count(),
        }
        counts["total"] = sum(counts.values())

        return Response(
            {
                "entity": JawafEntitySerializer(entity).data,
                "relationships": relationships_data,
                "counts": counts,
            }
        )


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
    tags=["statistics"],
    responses={
        200: {
            "type": "object",
            "properties": {
                "published_cases": {"type": "integer", "example": 127},
                "cases_under_investigation": {"type": "integer", "example": 43},
                "cases_closed": {"type": "integer", "example": 31},
                "entities_tracked": {"type": "integer", "example": 89},
                "last_updated": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-12-04T10:30:00Z",
                },
            },
        }
    },
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
        cache_key = "stats-cache"

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        # Calculate statistics
        stats = {
            "published_cases": Case.objects.filter(state=CaseState.PUBLISHED).count(),
            "cases_under_investigation": Case.objects.filter(
                state__in=[CaseState.DRAFT, CaseState.IN_REVIEW]
            ).count(),
            "cases_closed": Case.objects.filter(state=CaseState.CLOSED).count(),
            "entities_tracked": JawafEntity.objects.count(),
            "last_updated": timezone.now().isoformat(),
        }

        # Cache for 5 minutes
        cache.set(cache_key, stats, timeout=300)

        return Response(stats)


@extend_schema_view(
    get=extend_schema(
        summary="Advanced entity relationship queries",
        description="""
        Perform complex queries across entity relationships with advanced filtering and aggregation.
        
        **Query capabilities:**
        - Find entities with specific relationship type combinations
        - Filter by case states and date ranges
        - Get aggregated statistics across the system
        - Support complex boolean logic for relationship types
        
        **Query Parameters:**
        - `has_relationship_types`: Comma-separated list of relationship types the entity must have
        - `case_states`: Filter by case states (default: PUBLISHED,IN_REVIEW)
        - `case_start_date_after`: Filter cases that started after this date (YYYY-MM-DD)
        - `case_start_date_before`: Filter cases that started before this date (YYYY-MM-DD)
        - `min_case_count`: Minimum number of cases the entity must be involved in
        - `include_counts`: Include detailed counts in response (default: true)
        
        **Examples:**
        - Find entities that are both alleged and witnesses: `?has_relationship_types=alleged,witness`
        - Find entities in recent cases: `?case_start_date_after=2024-01-01`
        - Find highly involved entities: `?min_case_count=5`
        """,
        parameters=[
            OpenApiParameter(
                name="has_relationship_types",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Entity must have ALL of these relationship types (comma-separated)",
                required=False,
                examples=[
                    OpenApiExample("Alleged entities", value="alleged"),
                    OpenApiExample("Alleged and witnesses", value="alleged,witness"),
                ],
            ),
            OpenApiParameter(
                name="case_states",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by case states (default: PUBLISHED,IN_REVIEW)",
                required=False,
            ),
            OpenApiParameter(
                name="case_start_date_after",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Cases started after this date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="case_start_date_before",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Cases started before this date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="min_case_count",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Minimum number of cases entity must be involved in",
                required=False,
            ),
            OpenApiParameter(
                name="include_counts",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Include detailed relationship counts (default: true)",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity": {"$ref": "#/components/schemas/JawafEntity"},
                                "relationship_counts": {
                                    "type": "object",
                                    "properties": {
                                        "alleged": {"type": "integer"},
                                        "related": {"type": "integer"},
                                        "witness": {"type": "integer"},
                                        "opposition": {"type": "integer"},
                                        "victim": {"type": "integer"},
                                        "total_cases": {"type": "integer"},
                                    },
                                },
                                "recent_cases": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "case_id": {"type": "string"},
                                            "title": {"type": "string"},
                                            "relationship_types": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "summary": {
                        "type": "object",
                        "properties": {
                            "total_entities": {"type": "integer"},
                            "total_relationships": {"type": "integer"},
                            "relationship_type_distribution": {
                                "type": "object",
                                "properties": {
                                    "alleged": {"type": "integer"},
                                    "related": {"type": "integer"},
                                    "witness": {"type": "integer"},
                                    "opposition": {"type": "integer"},
                                    "victim": {"type": "integer"},
                                },
                            },
                        },
                    },
                },
            }
        },
        tags=["relationships"],
    )
)
class EntityRelationshipQueryView(APIView):
    """
    Advanced API endpoint for complex entity relationship queries.

    Supports complex filtering and aggregation across entity relationships
    to enable sophisticated analysis of the accountability data.
    """

    def get(self, request):
        """
        GET /api/entity-relationships/query/

        Perform advanced queries across entity relationships.
        """
        from django.db.models import Count, Q
        from datetime import datetime

        # Parse query parameters
        has_relationship_types = request.query_params.get("has_relationship_types")
        case_states = request.query_params.get("case_states", "PUBLISHED,IN_REVIEW")
        case_start_date_after = request.query_params.get("case_start_date_after")
        case_start_date_before = request.query_params.get("case_start_date_before")
        min_case_count = request.query_params.get("min_case_count")
        include_counts = (
            request.query_params.get("include_counts", "true").lower() == "true"
        )

        # Validate case states
        case_states_list = [s.strip() for s in case_states.split(",")]
        valid_states = [choice[0] for choice in CaseState.choices]
        invalid_states = [s for s in case_states_list if s not in valid_states]
        if invalid_states:
            return Response(
                {
                    "error": f"Invalid case state(s): {', '.join(invalid_states)}",
                    "valid_states": valid_states,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build base queryset
        entities_qs = JawafEntity.objects.all()

        # Filter by case states
        case_filter = Q(case_relationships__case__state__in=case_states_list)

        # Add date filters if provided
        if case_start_date_after:
            try:
                date_after = datetime.strptime(case_start_date_after, "%Y-%m-%d").date()
                case_filter &= Q(
                    case_relationships__case__case_start_date__gte=date_after
                )
            except ValueError:
                return Response(
                    {
                        "error": "Invalid date format for case_start_date_after. Use YYYY-MM-DD."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if case_start_date_before:
            try:
                date_before = datetime.strptime(
                    case_start_date_before, "%Y-%m-%d"
                ).date()
                case_filter &= Q(
                    case_relationships__case__case_start_date__lte=date_before
                )
            except ValueError:
                return Response(
                    {
                        "error": "Invalid date format for case_start_date_before. Use YYYY-MM-DD."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Apply case filters
        entities_qs = entities_qs.filter(case_filter).distinct()

        # Filter by required relationship types
        if has_relationship_types:
            required_types = [t.strip() for t in has_relationship_types.split(",")]

            # Validate relationship types
            valid_types = [choice[0] for choice in RelationshipType.choices]
            invalid_types = [t for t in required_types if t not in valid_types]
            if invalid_types:
                return Response(
                    {
                        "error": f"Invalid relationship type(s): {', '.join(invalid_types)}",
                        "valid_types": valid_types,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Entity must have ALL required relationship types
            for rel_type in required_types:
                entities_qs = entities_qs.filter(
                    case_relationships__relationship_type=rel_type,
                    case_relationships__case__state__in=case_states_list,
                ).distinct()

        # Filter by minimum case count
        if min_case_count:
            try:
                min_count = int(min_case_count)
                entities_qs = entities_qs.annotate(
                    case_count=Count("case_relationships__case", distinct=True)
                ).filter(case_count__gte=min_count)
            except ValueError:
                return Response(
                    {"error": "min_case_count must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Limit results for performance
        entities_qs = entities_qs[:100]  # Limit to 100 entities

        # Build response data
        entities_data = []
        total_relationships = 0
        relationship_type_distribution = {
            "alleged": 0,
            "related": 0,
            "witness": 0,
            "opposition": 0,
            "victim": 0,
        }

        for entity in entities_qs:
            entity_data = {
                "entity": JawafEntitySerializer(entity).data,
            }

            if include_counts:
                # Get relationship counts for this entity
                relationships = entity.case_relationships.filter(
                    case__state__in=case_states_list
                )

                counts = {
                    "alleged": relationships.filter(
                        relationship_type=RelationshipType.ALLEGED
                    ).count(),
                    "related": relationships.filter(
                        relationship_type=RelationshipType.RELATED
                    ).count(),
                    "witness": relationships.filter(
                        relationship_type=RelationshipType.WITNESS
                    ).count(),
                    "opposition": relationships.filter(
                        relationship_type=RelationshipType.OPPOSITION
                    ).count(),
                    "victim": relationships.filter(
                        relationship_type=RelationshipType.VICTIM
                    ).count(),
                }
                counts["total_cases"] = relationships.values("case").distinct().count()

                entity_data["relationship_counts"] = counts

                # Update global distribution
                for rel_type, count in counts.items():
                    if rel_type != "total_cases":
                        relationship_type_distribution[rel_type] += count
                        total_relationships += count

                # Get recent cases for this entity
                recent_cases = []
                for case_rel in relationships.select_related("case").order_by(
                    "-case__created_at"
                )[:5]:
                    case_data = {
                        "case_id": case_rel.case.case_id,
                        "title": case_rel.case.title,
                        "relationship_types": [case_rel.relationship_type],
                    }

                    # Check if this case is already in recent_cases and add relationship type
                    existing_case = next(
                        (
                            c
                            for c in recent_cases
                            if c["case_id"] == case_data["case_id"]
                        ),
                        None,
                    )
                    if existing_case:
                        if (
                            case_rel.relationship_type
                            not in existing_case["relationship_types"]
                        ):
                            existing_case["relationship_types"].append(
                                case_rel.relationship_type
                            )
                    else:
                        recent_cases.append(case_data)

                entity_data["recent_cases"] = recent_cases

            entities_data.append(entity_data)

        # Build summary
        summary = {
            "total_entities": len(entities_data),
            "total_relationships": total_relationships,
            "relationship_type_distribution": relationship_type_distribution,
        }

        return Response({"entities": entities_data, "summary": summary})


class FeedbackRateThrottle(AnonRateThrottle):
    """Rate throttle for feedback submissions: 5 per hour."""

    rate = "5/hour"


@extend_schema(
    summary="Submit platform feedback",
    description="""
    Submit feedback, bug reports, feature requests, or general comments about the platform.
    
    Rate limited to 5 submissions per IP address per hour.
    Contact information is optional - anonymous submissions are welcome.
    """,
    request=FeedbackSerializer,
    responses={
        201: FeedbackSerializer,
        400: OpenApiTypes.OBJECT,
        429: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Bug Report",
            value={
                "feedbackType": "bug",
                "subject": "Search not working on Cases page",
                "description": "When I try to search for cases, nothing happens.",
                "relatedPage": "Cases page",
                "contactInfo": {
                    "name": "राम बहादुर",
                    "contactMethods": [{"type": "email", "value": "ram@example.com"}],
                },
            },
            request_only=True,
        ),
        OpenApiExample(
            "Anonymous Feedback",
            value={
                "feedbackType": "general",
                "subject": "Great platform",
                "description": "This platform is very helpful!",
            },
            request_only=True,
        ),
    ],
)
class FeedbackView(APIView):
    """API view for submitting platform feedback."""

    throttle_classes = [FeedbackRateThrottle]

    def post(self, request):
        """Handle feedback submission."""
        serializer = FeedbackSerializer(data=request.data)

        if serializer.is_valid():
            # Capture metadata
            feedback = serializer.save(
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            return Response(
                serializer.to_representation(feedback), status=status.HTTP_201_CREATED
            )

        return Response(
            {"error": "Validation error", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
