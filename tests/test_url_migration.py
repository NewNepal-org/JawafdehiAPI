"""
Tests for URL field migration from URLField to JSONField.

These tests verify the post-migration behavior of the url field:
- Confirms the field accepts and stores lists of URLs
- Validates serialization works correctly with the new JSONField type
- Ensures backward compatibility with the new schema

Note: The actual migration logic is in cases/migrations/0010_change_url_to_jsonfield.py
which converts existing string URLs to JSON arrays during deployment.
"""
import pytest
from cases.models import DocumentSource


@pytest.mark.django_db
class TestURLMigration:
    """Test suite for URL field after migration to JSONField."""

    def test_url_field_stores_list(self):
        """Verify url field accepts and persists a list of URLs."""
        source = DocumentSource.objects.create(
            title="Test Source",
            url=["https://example.com"]
        )
        
        assert isinstance(source.url, list)
        assert source.url == ["https://example.com"]

    def test_multiple_urls_storage(self):
        """Verify multiple URLs can be stored and retrieved."""
        urls = ["https://example.com", "https://backup.example.com"]
        source = DocumentSource.objects.create(title="Test Source", url=urls)
        
        source.refresh_from_db()
        assert source.url == urls

    def test_url_serialization(self):
        """Verify URLs serialize correctly in API responses."""
        from cases.serializers import DocumentSourceSerializer
        
        source = DocumentSource.objects.create(
            title="Test Source",
            url=["https://example.com", "https://backup.com"]
        )
        
        serializer = DocumentSourceSerializer(source)
        assert serializer.data['url'] == ["https://example.com", "https://backup.com"]
