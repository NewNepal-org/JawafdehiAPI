"""
Tests for DocumentSource source_type field.
"""
import pytest
from django.core.exceptions import ValidationError
from cases.models import DocumentSource, SourceType


@pytest.mark.django_db
class TestSourceTypeField:
    """Test suite for source_type field in DocumentSource model."""

    def test_source_type_default_value(self):
        """Test that source_type defaults to OTHER."""
        source = DocumentSource.objects.create(
            title="Test Source"
        )
        assert source.source_type == SourceType.OTHER

    def test_source_type_choices(self):
        """Test that all source type choices are valid."""
        valid_types = [
            SourceType.OFFICIAL_GOVERNMENT,
            SourceType.MEDIA_NEWS,
            SourceType.SOCIAL_MEDIA,
            SourceType.INTERNAL_DOCUMENT,
            SourceType.ACADEMIC_RESEARCH,
            SourceType.LEGAL_DOCUMENT,
            SourceType.WHISTLEBLOWER,
            SourceType.OTHER,
        ]
        
        for source_type in valid_types:
            source = DocumentSource.objects.create(
                title=f"Test Source - {source_type}",
                source_type=source_type
            )
            assert source.source_type == source_type
            source.delete()

    def test_source_type_display_labels(self):
        """Test that source type display labels are correct."""
        expected_labels = {
            SourceType.OFFICIAL_GOVERNMENT: "Official (Government)",
            SourceType.MEDIA_NEWS: "Media/News",
            SourceType.SOCIAL_MEDIA: "Social Media",
            SourceType.INTERNAL_DOCUMENT: "Internal Document",
            SourceType.ACADEMIC_RESEARCH: "Academic/Research",
            SourceType.LEGAL_DOCUMENT: "Legal Document",
            SourceType.WHISTLEBLOWER: "Whistleblower",
            SourceType.OTHER: "Other",
        }
        
        for source_type, expected_label in expected_labels.items():
            source = DocumentSource.objects.create(
                title=f"Test Source - {source_type}",
                source_type=source_type
            )
            assert source.get_source_type_display() == expected_label
            source.delete()

    def test_source_type_filtering(self):
        """Test filtering sources by type."""
        # Create sources of different types
        gov_source = DocumentSource.objects.create(
            title="Government Report",
            source_type=SourceType.OFFICIAL_GOVERNMENT
        )
        media_source = DocumentSource.objects.create(
            title="News Article",
            source_type=SourceType.MEDIA_NEWS
        )
        other_source = DocumentSource.objects.create(
            title="Other Source",
            source_type=SourceType.OTHER
        )
        
        # Test filtering
        gov_sources = DocumentSource.objects.filter(
            source_type=SourceType.OFFICIAL_GOVERNMENT
        )
        assert gov_sources.count() == 1
        assert gov_sources.first() == gov_source
        
        media_sources = DocumentSource.objects.filter(
            source_type=SourceType.MEDIA_NEWS
        )
        assert media_sources.count() == 1
        assert media_sources.first() == media_source

    def test_source_type_in_serializer(self):
        """Test that source_type is included in serializer."""
        from cases.serializers import DocumentSourceSerializer
        
        source = DocumentSource.objects.create(
            title="Test Source",
            source_type=SourceType.MEDIA_NEWS
        )
        
        serializer = DocumentSourceSerializer(source)
        assert 'source_type' in serializer.data
        assert serializer.data['source_type'] == SourceType.MEDIA_NEWS

    def test_source_type_update(self):
        """Test updating source_type."""
        source = DocumentSource.objects.create(
            title="Test Source",
            source_type=SourceType.OTHER
        )
        
        # Update source type
        source.source_type = SourceType.OFFICIAL_GOVERNMENT
        source.save()
        
        # Verify update
        source.refresh_from_db()
        assert source.source_type == SourceType.OFFICIAL_GOVERNMENT

    def test_source_type_statistics(self):
        """Test generating statistics by source type."""
        from django.db.models import Count
        
        # Create multiple sources of different types
        for _ in range(3):
            DocumentSource.objects.create(
                title=f"Gov Source {_}",
                source_type=SourceType.OFFICIAL_GOVERNMENT
            )
        
        for _ in range(2):
            DocumentSource.objects.create(
                title=f"Media Source {_}",
                source_type=SourceType.MEDIA_NEWS
            )
        
        # Get statistics
        stats = DocumentSource.objects.values('source_type').annotate(
            count=Count('id')
        )
        
        stats_dict = {item['source_type']: item['count'] for item in stats}
        assert stats_dict.get(SourceType.OFFICIAL_GOVERNMENT, 0) == 3
        assert stats_dict.get(SourceType.MEDIA_NEWS, 0) == 2
