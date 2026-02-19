"""
Tests for URL field migration from URLField to JSONField.
"""
import pytest
from django.test import TransactionTestCase
from cases.models import DocumentSource


class TestURLMigration(TransactionTestCase):
    """Test suite for URL field migration."""

    def test_url_field_is_list(self):
        """Test that url field stores data as a list."""
        source = DocumentSource.objects.create(
            title="Test Source",
            url=["https://example.com"]
        )
        
        assert isinstance(source.url, list)
        assert len(source.url) == 1
        assert source.url[0] == "https://example.com"

    def test_empty_url_list(self):
        """Test that empty URL list is handled correctly."""
        source = DocumentSource.objects.create(
            title="Test Source",
            url=[]
        )
        
        assert isinstance(source.url, list)
        assert len(source.url) == 0

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

    def test_url_field_default(self):
        """Test that url field defaults to empty list."""
        source = DocumentSource.objects.create(
            title="Test Source"
        )
        
        assert isinstance(source.url, list)
        assert len(source.url) == 0

    def test_url_update(self):
        """Test updating URL list."""
        source = DocumentSource.objects.create(
            title="Test Source",
            url=["https://example.com"]
        )
        
        # Add more URLs
        source.url.append("https://backup.example.com")
        source.save()
        
        source.refresh_from_db()
        assert len(source.url) == 2
        assert "https://backup.example.com" in source.url

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

    def test_url_validation(self):
        """Test that invalid URLs are handled."""
        # This should work - Django doesn't validate URLs in JSONField
        source = DocumentSource.objects.create(
            title="Test Source",
            url=["not-a-valid-url"]
        )
        
        assert isinstance(source.url, list)
        assert source.url[0] == "not-a-valid-url"

    def test_migrated_data_format(self):
        """
        Test that data migrated from URLField to JSONField
        maintains the correct format.
        """
        # Simulate migrated data (single URL converted to list)
        source = DocumentSource.objects.create(
            title="Migrated Source",
            url=["https://old-url.com"]
        )
        
        source.refresh_from_db()
        
        # Verify it's a list with one item
        assert isinstance(source.url, list)
        assert len(source.url) == 1
        assert source.url[0] == "https://old-url.com"
