"""
Minimal test coverage for source_type field on DocumentSource.

Verifies field persistence, serialization, and valid enum values.
"""
import pytest
from cases.models import DocumentSource, SourceType


@pytest.mark.django_db
class TestSourceTypeField:
    """Test suite for source_type field."""

    def test_source_type_persistence(self):
        """Verify source_type field persists valid enum values."""
        source = DocumentSource.objects.create(
            title="Test Source",
            source_type=SourceType.MEDIA_NEWS
        )
        
        source.refresh_from_db()
        assert source.source_type == SourceType.MEDIA_NEWS

    def test_source_type_nullable(self):
        """Verify source_type can be null."""
        source = DocumentSource.objects.create(
            title="Test Source",
            source_type=None
        )
        
        source.refresh_from_db()
        assert source.source_type is None

    def test_source_type_serialization(self):
        """Verify source_type serializes correctly in API responses."""
        from cases.serializers import DocumentSourceSerializer
        
        source = DocumentSource.objects.create(
            title="Test Source",
            source_type=SourceType.LEGAL_COURT_ORDER
        )
        
        serializer = DocumentSourceSerializer(source)
        assert serializer.data['source_type'] == "LEGAL_COURT_ORDER"
