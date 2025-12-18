"""
Tests for Agni Django admin interface.

Tests the admin UI for document upload, session management, and entity processing.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.urls import reverse

from agni.admin import StoredExtractionSessionAdmin, ApprovedEntityChangeAdmin
from agni.models import StoredExtractionSession, ApprovedEntityChange
from tests.conftest import create_user_with_role


@pytest.mark.django_db
class TestStoredExtractionSessionAdmin:
    """Test admin interface for StoredExtractionSession model."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = StoredExtractionSessionAdmin(StoredExtractionSession, self.site)
        
        # Create test users
        self.admin_user = create_user_with_role("admin", "admin@test.com", "Admin")
        self.contributor_user = create_user_with_role("contributor", "contributor@test.com", "Contributor")
    
    def test_session_list_displays_required_columns(self):
        """Test that admin displays session list with status, date, user columns."""
        # Create test sessions
        session1 = StoredExtractionSession.objects.create(
            document="test1.pdf",
            status="pending",
            created_by=self.admin_user
        )
        session2 = StoredExtractionSession.objects.create(
            document="test2.pdf", 
            status="completed",
            created_by=self.contributor_user
        )
        
        # Create mock request
        request = self.factory.get('/admin/agni/storedextractionsession/')
        request.user = self.admin_user
        
        # Get changelist view
        changelist = self.admin.get_changelist_instance(request)
        
        # Verify sessions are displayed
        queryset = changelist.get_queryset(request)
        assert session1 in queryset
        assert session2 in queryset
        
        # Verify list_display includes required columns
        expected_columns = ['id', 'document', 'status', 'created_by', 'created_at', 'updated_at']
        for column in expected_columns:
            assert column in self.admin.list_display
    
    def test_session_list_filtering_by_status(self):
        """Test filtering by status works."""
        # Create sessions with different statuses
        pending_session = StoredExtractionSession.objects.create(
            document="pending.pdf",
            status="pending",
            created_by=self.admin_user
        )
        completed_session = StoredExtractionSession.objects.create(
            document="completed.pdf",
            status="completed", 
            created_by=self.admin_user
        )
        
        # Create mock request with status filter
        request = self.factory.get('/admin/agni/storedextractionsession/?status=pending')
        request.user = self.admin_user
        
        # Get changelist view
        changelist = self.admin.get_changelist_instance(request)
        
        # Apply filters
        filtered_queryset = changelist.get_queryset(request)
        
        # Verify filtering works
        assert pending_session in filtered_queryset
        assert completed_session not in filtered_queryset
        
        # Verify status is in list_filter
        assert 'status' in self.admin.list_filter
    
    def test_session_list_filtering_by_user(self):
        """Test filtering by user works."""
        # Create sessions for different users
        admin_session = StoredExtractionSession.objects.create(
            document="admin.pdf",
            status="pending",
            created_by=self.admin_user
        )
        contributor_session = StoredExtractionSession.objects.create(
            document="contributor.pdf",
            status="pending",
            created_by=self.contributor_user
        )
        
        # Create mock request with user filter
        request = self.factory.get(f'/admin/agni/storedextractionsession/?created_by={self.admin_user.id}')
        request.user = self.admin_user
        
        # Get changelist view
        changelist = self.admin.get_changelist_instance(request)
        
        # Apply filters
        filtered_queryset = changelist.get_queryset(request)
        
        # Verify filtering works
        assert admin_session in filtered_queryset
        assert contributor_session not in filtered_queryset
        
        # Verify created_by is in list_filter
        assert 'created_by' in self.admin.list_filter


@pytest.mark.django_db
class TestApprovedEntityChangeAdmin:
    """Test admin interface for ApprovedEntityChange model."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = ApprovedEntityChangeAdmin(ApprovedEntityChange, self.site)
        
        # Create test user
        self.admin_user = create_user_with_role("admin", "admin@test.com", "Admin")
    
    def test_change_list_displays_required_columns(self):
        """Test that admin displays change list with required columns."""
        # Create test change
        change = ApprovedEntityChange.objects.create(
            change_type="create",
            entity_type="person",
            entity_sub_type="politician",
            entity_data={"name": "Test Person"},
            description="Test change",
            approved_by=self.admin_user
        )
        
        # Create mock request
        request = self.factory.get('/admin/agni/approvedentitychange/')
        request.user = self.admin_user
        
        # Get changelist view
        changelist = self.admin.get_changelist_instance(request)
        
        # Verify change is displayed
        queryset = changelist.get_queryset(request)
        assert change in queryset
        
        # Verify list_display includes required columns
        expected_columns = ['id', 'change_type', 'entity_type', 'entity_sub_type', 'approved_by', 'approved_at']
        for column in expected_columns:
            assert column in self.admin.list_display
    
    def test_change_list_filtering_works(self):
        """Test that filtering by change_type and entity_type works."""
        # Create changes with different types
        create_change = ApprovedEntityChange.objects.create(
            change_type="create",
            entity_type="person",
            entity_data={"name": "New Person"},
            approved_by=self.admin_user
        )
        update_change = ApprovedEntityChange.objects.create(
            change_type="update",
            entity_type="organization",
            entity_data={"name": "Updated Org"},
            approved_by=self.admin_user
        )
        
        # Test filtering by change_type
        request = self.factory.get('/admin/agni/approvedentitychange/?change_type=create')
        request.user = self.admin_user
        
        changelist = self.admin.get_changelist_instance(request)
        filtered_queryset = changelist.get_queryset(request)
        
        assert create_change in filtered_queryset
        assert update_change not in filtered_queryset
        
        # Verify filters are configured
        assert 'change_type' in self.admin.list_filter
        assert 'entity_type' in self.admin.list_filter


@pytest.mark.django_db
class TestDocumentUploadWorkflow:
    """Test admin UI for document upload workflow."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = StoredExtractionSessionAdmin(StoredExtractionSession, self.site)
        
        # Create test user
        self.admin_user = create_user_with_role("admin", "admin@test.com", "Admin")
    
    def test_upload_form_accepts_valid_file_types(self):
        """Test that upload form accepts valid file types."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Test each valid file type
        valid_files = [
            ('test.txt', b'Test content'),
            ('test.md', b'# Test markdown'),
            ('test.doc', b'Test doc content'),
            ('test.docx', b'Test docx content'),
            ('test.pdf', b'Test pdf content'),
        ]
        
        for filename, content in valid_files:
            # Test file type validation directly
            from agni.utils import validate_file_type
            assert validate_file_type(filename), f"File {filename} should be accepted"
    
    def test_upload_form_rejects_invalid_file_types_with_error_message(self):
        """Test that upload form rejects invalid file types with error message."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from agni.utils import get_file_validation_error
        
        # Test invalid file types
        invalid_files = [
            ('test.exe', b'Executable content'),
            ('test.jpg', b'Image content'),
            ('test.zip', b'Archive content'),
        ]
        
        for filename, content in invalid_files:
            # Verify validation error is returned
            error_message = get_file_validation_error(filename)
            assert error_message is not None, f"File {filename} should be rejected with error message"
            assert "Unsupported file type" in error_message
            assert filename.split('.')[-1] in error_message.lower()
    
    def test_guidance_textarea_is_optional(self):
        """Test that guidance textarea is optional."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create valid file upload without guidance
        uploaded_file = SimpleUploadedFile('test.txt', b'Test content')
        
        # Create session without guidance
        session = StoredExtractionSession.objects.create(
            document=uploaded_file,
            created_by=self.admin_user,
            session_data={'guidance': ''}  # Empty guidance should be allowed
        )
        
        assert session.id is not None
        assert session.session_data.get('guidance') == ''
    
    def test_successful_upload_creates_session(self):
        """Test that successful upload creates session."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create valid file upload
        uploaded_file = SimpleUploadedFile('test.txt', b'Test content')
        
        # Create session
        session = StoredExtractionSession.objects.create(
            document=uploaded_file,
            created_by=self.admin_user,
            session_data={'guidance': 'Test guidance'}
        )
        
        # Verify session was created
        assert session.id is not None
        assert 'test' in session.document.name and '.txt' in session.document.name
        assert session.created_by == self.admin_user
        assert session.session_data.get('guidance') == 'Test guidance'
        assert session.status == 'pending'
    
    def test_upload_generates_unique_session_id(self):
        """Test that each upload generates a unique session ID."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            uploaded_file = SimpleUploadedFile(f'test{i}.txt', b'Test content')
            session = StoredExtractionSession.objects.create(
                document=uploaded_file,
                created_by=self.admin_user
            )
            sessions.append(session)
        
        # Verify all IDs are unique
        session_ids = [session.id for session in sessions]
        assert len(set(session_ids)) == len(session_ids), "All session IDs should be unique"