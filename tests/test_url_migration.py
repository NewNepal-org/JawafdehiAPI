"""
Tests for URL field migration from URLField to JSONField.

These tests verify both the migration process and post-migration behavior:
- Tests the actual migration logic that converts string URLs to lists
- Confirms the field accepts and stores lists of URLs after migration
- Validates serialization works correctly with the new JSONField type
"""
import pytest
from django.test import TransactionTestCase
from django.db import connection
from django.core.management import call_command
from cases.models import DocumentSource


class TestURLMigrationProcess(TransactionTestCase):
    """
    Test the actual migration process from URLField to JSONField.
    
    Uses TransactionTestCase to allow migration testing with database schema changes.
    """
    
    # Specify which migrations to start from and migrate to
    migrate_from = [('cases', '0009_merge_20260112_0309')]
    migrate_to = [('cases', '0010_change_url_to_jsonfield')]
    
    def setUp(self):
        """Set up test by migrating to the state before our migration."""
        # Migrate to the state before our URL migration
        call_command('migrate', 'cases', '0009_merge_20260112_0309', verbosity=0)
        
        # Get the model at the old schema state
        from django.apps import apps
        from django.utils import timezone
        DocumentSource = apps.get_model('cases', 'DocumentSource')
        
        # Create test data with old URLField format (single string)
        # Use timezone.now() for timestamps (works with both SQLite and PostgreSQL)
        now = timezone.now()
        with connection.cursor() as cursor:
            # SQLite uses datetime() function, not NOW()
            cursor.execute("""
                INSERT INTO cases_documentsource 
                (source_id, title, description, url, is_deleted, created_at, updated_at)
                VALUES 
                ('source:test:001', 'Test Source 1', 'Description 1', 'https://example.com/doc1.pdf', 0, ?, ?),
                ('source:test:002', 'Test Source 2', 'Description 2', 'https://example.com/doc2.pdf', 0, ?, ?),
                ('source:test:003', 'Empty URL Source', 'Description 3', '', 0, ?, ?),
                ('source:test:004', 'Null URL Source', 'Description 4', NULL, 0, ?, ?)
            """, [now, now, now, now, now, now, now, now])
    
    def test_migration_converts_string_urls_to_lists(self):
        """Test that migration converts single URL strings to JSON arrays."""
        # Run the migration
        call_command('migrate', 'cases', '0010_change_url_to_jsonfield', verbosity=0)
        
        # Verify the data was converted correctly
        source1 = DocumentSource.objects.get(source_id='source:test:001')
        assert isinstance(source1.url, list), "URL should be converted to list"
        assert source1.url == ['https://example.com/doc1.pdf'], "URL should be wrapped in list"
        
        source2 = DocumentSource.objects.get(source_id='source:test:002')
        assert source2.url == ['https://example.com/doc2.pdf']
    
    def test_migration_handles_empty_urls(self):
        """Test that migration converts empty strings to empty lists."""
        call_command('migrate', 'cases', '0010_change_url_to_jsonfield', verbosity=0)
        
        source = DocumentSource.objects.get(source_id='source:test:003')
        assert source.url == [], "Empty string should become empty list"
    
    def test_migration_handles_null_urls(self):
        """Test that migration converts NULL values to empty lists."""
        call_command('migrate', 'cases', '0010_change_url_to_jsonfield', verbosity=0)
        
        source = DocumentSource.objects.get(source_id='source:test:004')
        assert source.url == [], "NULL should become empty list"
    
    def test_reverse_migration_converts_lists_back_to_strings(self):
        """Test that reverse migration converts lists back to single URL strings."""
        # First migrate forward
        call_command('migrate', 'cases', '0010_change_url_to_jsonfield', verbosity=0)
        
        # Verify forward migration worked
        source = DocumentSource.objects.get(source_id='source:test:001')
        assert isinstance(source.url, list)
        
        # Now migrate backward
        call_command('migrate', 'cases', '0009_merge_20260112_0309', verbosity=0)
        
        # Verify reverse migration worked (takes first URL from list)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT url FROM cases_documentsource WHERE source_id = 'source:test:001'"
            )
            url_value = cursor.fetchone()[0]
            assert url_value == 'https://example.com/doc1.pdf', "Should revert to first URL string"


@pytest.mark.django_db
class TestURLFieldPostMigration:
    """Test suite for URL field behavior after migration to JSONField."""

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

