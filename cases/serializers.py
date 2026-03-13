"""
Serializers for the Jawafdehi accountability platform API.

See: .kiro/specs/accountability-platform-core/design.md
"""

from rest_framework import serializers
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Case, DocumentSource, JawafEntity, CaseState, Feedback


class JawafEntitySerializer(serializers.ModelSerializer):
    """
    Serializer for JawafEntity model.

    Maintains backward compatibility by returning separate
    alleged_cases and related_cases arrays.
    """

    alleged_cases = serializers.SerializerMethodField(
        help_text="List of case IDs where this entity is alleged"
    )
    related_cases = serializers.SerializerMethodField(
        help_text="List of case IDs where this entity is related or a location"
    )

    class Meta:
        model = JawafEntity
        fields = ["id", "nes_id", "display_name", "alleged_cases", "related_cases"]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_alleged_cases(self, obj):
        """
        Get list of case IDs where this entity is alleged.

        Uses new CaseEntityRelationship model with type='alleged'.
        Only includes PUBLISHED cases (and IN_REVIEW if feature flag is enabled).
        """
        from django.conf import settings
        from .models import CaseEntityRelationship

        if settings.EXPOSE_CASES_IN_REVIEW:
            relationships = obj.case_relationships.filter(
                type=CaseEntityRelationship.RelationshipType.ALLEGED,
                case__state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW],
            )
        else:
            relationships = obj.case_relationships.filter(
                type=CaseEntityRelationship.RelationshipType.ALLEGED,
                case__state=CaseState.PUBLISHED,
            )

        return sorted(
            relationships.values_list("case__case_id", flat=True).distinct()
        )

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_related_cases(self, obj):
        """
        Get list of case IDs where this entity is related or a location.

        Uses new CaseEntityRelationship model with type='related'.
        Also includes location relationships (unchanged).
        Only includes PUBLISHED cases (and IN_REVIEW if feature flag is enabled).
        """
        from django.conf import settings
        from .models import CaseEntityRelationship

        # Get related relationships
        if settings.EXPOSE_CASES_IN_REVIEW:
            related_relationships = obj.case_relationships.filter(
                type=CaseEntityRelationship.RelationshipType.RELATED,
                case__state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW],
            )
            location_cases = obj.cases_as_location.filter(
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW]
            )
        else:
            related_relationships = obj.case_relationships.filter(
                type=CaseEntityRelationship.RelationshipType.RELATED,
                case__state=CaseState.PUBLISHED,
            )
            location_cases = obj.cases_as_location.filter(state=CaseState.PUBLISHED)

        # Combine and deduplicate
        case_ids = set(related_relationships.values_list("case__case_id", flat=True))
        case_ids.update(location_cases.values_list("case_id", flat=True))

        # Exclude cases where this entity is already alleged (alleged takes precedence)
        # Use same visibility rules as related_relationships
        if settings.EXPOSE_CASES_IN_REVIEW:
            alleged_case_ids = set(
                obj.case_relationships.filter(
                    type=CaseEntityRelationship.RelationshipType.ALLEGED,
                    case__state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW],
                ).values_list("case__case_id", flat=True)
            )
        else:
            alleged_case_ids = set(
                obj.case_relationships.filter(
                    type=CaseEntityRelationship.RelationshipType.ALLEGED,
                    case__state=CaseState.PUBLISHED,
                ).values_list("case__case_id", flat=True)
            )
        case_ids -= alleged_case_ids

        return sorted(case_ids)


class CaseSerializer(serializers.ModelSerializer):
    """
    Serializer for Case model with unified entities array.
    """

    entities = serializers.SerializerMethodField(
        help_text="List of entities with type indicators"
    )
    locations = JawafEntitySerializer(many=True, read_only=True)
    tags = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of tags for categorization (e.g., 'land-encroachment', 'national-interest')",
        required=False,
    )
    key_allegations = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of key allegation statements",
        required=False,
    )
    timeline = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of timeline entries with date, title, and description",
        required=False,
    )
    evidence = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of evidence entries with source_id and description",
        required=False,
    )
    versionInfo = serializers.JSONField(
        help_text="Version metadata tracking changes (version_number, user_id, change_summary, datetime)",
        required=False,
    )

    class Meta:
        model = Case
        fields = [
            "id",
            "case_id",
            "case_type",
            "state",
            "title",
            "short_description",
            "thumbnail_url",
            "banner_url",
            "case_start_date",
            "case_end_date",
            "entities",  # NEW: replaces alleged_entities and related_entities
            "locations",
            "tags",
            "description",
            "key_allegations",
            "timeline",
            "evidence",
            "versionInfo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields  # API is read-only

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_entities(self, obj):
        """
        Get unified entities array with type and notes fields.

        Returns a flat list of entity dicts (id, nes_id, display_name, type,
        optional notes).  Does NOT nest alleged_cases/related_cases — those
        belong on the /api/entities/ endpoint, not inside a case detail.
        """
        relationships = obj.entity_relationships.select_related("entity").all()

        entities_data = []
        for rel in relationships:
            entity_data = {
                "id": rel.entity_id,
                "nes_id": rel.entity.nes_id,
                "display_name": rel.entity.display_name,
                "type": rel.type,
            }
            if rel.notes:
                entity_data["notes"] = rel.notes
            entities_data.append(entity_data)

        return entities_data


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
        fields = CaseSerializer.Meta.fields + ["audit_history"]

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
                state__in=[CaseState.PUBLISHED, CaseState.IN_REVIEW],
            ).order_by("-version")
        else:
            all_versions = Case.objects.filter(
                case_id=obj.case_id, state=CaseState.PUBLISHED
            ).order_by("-version")

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
            "id",
            "source_id",
            "title",
            "description",
            "source_type",
            "url",
            "related_entities",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields  # API is read-only


class ContactMethodSerializer(serializers.Serializer):
    """Serializer for contact method within feedback."""

    type = serializers.ChoiceField(
        choices=["email", "phone", "whatsapp", "instagram", "facebook", "other"],
        help_text="Type of contact method",
    )
    value = serializers.CharField(
        max_length=300, help_text="Contact value (email, phone, username, etc.)"
    )


class ContactInfoSerializer(serializers.Serializer):
    """Serializer for contact information within feedback."""

    name = serializers.CharField(
        max_length=200, required=False, allow_blank=True, help_text="Submitter's name"
    )
    contactMethods = ContactMethodSerializer(
        many=True, required=False, help_text="List of contact methods"
    )


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for Feedback model."""

    feedbackType = serializers.CharField(
        source="feedback_type", help_text="Type of feedback"
    )
    relatedPage = serializers.CharField(
        source="related_page",
        required=False,
        allow_blank=True,
        help_text="Page or feature related to feedback",
    )
    contactInfo = ContactInfoSerializer(
        source="contact_info", required=False, help_text="Optional contact information"
    )
    submittedAt = serializers.DateTimeField(
        source="submitted_at",
        read_only=True,
        help_text="Timestamp when feedback was submitted",
    )

    class Meta:
        model = Feedback
        fields = [
            "id",
            "feedbackType",
            "subject",
            "description",
            "relatedPage",
            "contactInfo",
            "status",
            "submittedAt",
        ]
        read_only_fields = ["id", "status", "submittedAt"]

    def validate_feedbackType(self, value):
        """Validate feedback type."""
        from .models import FeedbackType

        valid_types = [choice[0] for choice in FeedbackType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid feedback type. Must be one of: {', '.join(valid_types)}"
            )
        return value

    def validate_contactInfo(self, value):
        """Validate contact info structure."""
        if not value:
            return {}

        # Validate contact methods if present
        if "contactMethods" in value:
            valid_types = [
                "email",
                "phone",
                "whatsapp",
                "instagram",
                "facebook",
                "other",
            ]
            for method in value["contactMethods"]:
                if method.get("type") not in valid_types:
                    raise serializers.ValidationError(
                        f"Invalid contact method type. Must be one of: {', '.join(valid_types)}"
                    )

        return value

    def to_representation(self, instance):
        """Convert to camelCase response format."""
        data = super().to_representation(instance)

        # Return simplified response for API
        return {
            "id": data["id"],
            "feedbackType": data["feedbackType"],
            "subject": data["subject"],
            "status": data["status"],
            "submittedAt": data["submittedAt"],
            "message": "Thank you for your feedback! We will review it and get back to you if needed.",
        }
