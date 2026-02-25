"""
Tests for URL field migration from URLField to JSONField.
"""
import pytest
from cases.models import DocumentSource


@pytest.mark.django_db
class TestURLMigration:
    """Test suite for URL field after migration to JSONField."""

    def test_url_field_is_list(self):
        """Test that url field stores data as a list."""
        source = DocumentSource.objects.create(
            title="Test Source",
            url=["https://example.com"]
        )
        
        assert isinstance(source.url, list)
        assert len(source.url) == 1
        assert source.url[0] == "https://example.com"

    def test_multiple_urls(self):
        """Test that multiple URLs can be stored."""
        urls = [
            "https://example.com",
            "https://backup.example.com",
            "https://mirror.example.com"
        ]
        
        source = DocumentSource.objects.create(
            title="Test Source",
            url=urls
        )
        
        source.refresh_from_db()
        assert isinstance(source.url, list)
        assert len(source.url) == 3
        assert source.url == urls

    def test_url_serialization(self):
        """Test that URLs are properly serialized in API."""
        from cases.serializers import DocumentSourceSerializer
        
        source = DocumentSource.objects.create(
            title="Test Source",
            url=["https://example.com", "https://backup.com"]
        )
        
        serializer = DocumentSourceSerializer(source)
        assert 'url' in serializer.data
        assert isinstance(serializer.data['url'], list)
        assert len(serializer.data['url']) == 2
