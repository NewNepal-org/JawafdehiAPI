"""
Unit tests for Agni document upload functionality.

Tests session creation, guidance storage, and unique ID generation.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User

from agni.models import StoredExtractionSession
from agni.forms import DocumentUploadForm
from tests.conftest import create_user_with_role


@pytest.mark.django_db
class TestDocumentUploadUnit:
    """Unit tests for document upload functionality."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        self.user = create_user_with_role("testuser", "test@example.com", "Contributor")
    
    def test_session_creation_with_valid_document(self):
        """Test session creation with valid document."""
        # Create valid document
        document = SimpleUploadedFile("test.txt", b"Test document content")
        
        # Create session
        session = StoredExtractionSession.objects.create(
            document=document,
            created_by=self.user,
            session_data={'guidance': 'Test guidance'}
        )
        
        # Verify session was created correctly
        assert session.id is not None
        assert 'test' in session.document.name and '.txt' in session.document.name
        assert session.created_by == self.user
        assert session.status == 'pending'
        assert session.session_data['guidance'] == 'Test guidance'
        assert session.created_at is not None
        assert session.updated_at is not None
    
    def test_session_stores_guidance_text(self):
        """Test session stores guidance text."""
        document = SimpleUploadedFile("guide_test.pdf", b"PDF content")
        guidance_text = "Please focus on extracting person names and organizations mentioned in the corruption case."
        
        # Create session with guidance
        session = StoredExtractionSession.objects.create(
            document=document,
            created_by=self.user,
            session_data={'guidance': guidance_text}
        )
        
        # Verify guidance is stored
        assert session.session_data['guidance'] == guidance_text
        
        # Verify guidance persists after save/reload
        session.refresh_from_db()
        assert session.session_data['guidance'] == guidance_text
    
    def test_session_stores_empty_guidance(self):
        """Test session can store empty guidance."""
        document = SimpleUploadedFile("no_guide.md", b"# Markdown content")
        
        # Create session without guidance
        session = StoredExtractionSession.objects.create(
            document=document,
            created_by=self.user,
            session_data={'guidance': ''}
        )
        
        # Verify empty guidance is stored
        assert session.session_data['guidance'] == ''
    
    def test_unique_session_id_generation(self):
        """Test unique session ID generation."""
        # Create multiple sessions
        sessions = []
        for i in range(5):
            document = SimpleUploadedFile(f"test{i}.txt", b"Content")
            session = StoredExtractionSession.objects.create(
                document=document,
                created_by=self.user,
                session_data={'guidance': f'Guidance {i}'}
            )
            sessions.append(session)
        
        # Verify all IDs are unique
        session_ids = [str(session.id) for session in sessions]
        assert len(set(session_ids)) == len(session_ids), "All session IDs should be unique"
        
        # Verify IDs are UUIDs (36 characters with hyphens)
        for session_id in session_ids:
            assert len(session_id) == 36
            assert session_id.count('-') == 4
    
    def test_session_default_status_is_pending(self):
        """Test that new sessions have default status of 'pending'."""
        document = SimpleUploadedFile("status_test.docx", b"DOCX content")
        
        session = StoredExtractionSession.objects.create(
            document=document,
            created_by=self.user
        )
        
        assert session.status == 'pending'
    
    def test_session_with_different_file_types(self):
        """Test session creation with different valid file types."""
        file_types = [
            ('test.txt', b'Text content'),
            ('test.md', b'# Markdown content'),
            ('test.doc', b'DOC content'),
            ('test.docx', b'DOCX content'),
            ('test.pdf', b'PDF content'),
        ]
        
        for filename, content in file_types:
            document = SimpleUploadedFile(filename, content)
            session = StoredExtractionSession.objects.create(
                document=document,
                created_by=self.user
            )
            
            assert session.id is not None
            # Django may add unique suffix, so check if original filename is in the path
            assert filename.split('.')[0] in session.document.name
            assert filename.split('.')[1] in session.document.name


@pytest.mark.django_db
class TestDocumentUploadForm:
    """Unit tests for DocumentUploadForm."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        self.user = create_user_with_role("formuser", "form@example.com", "Contributor")
    
    def test_form_saves_guidance_in_session_data(self):
        """Test that form saves guidance in session_data field."""
        document = SimpleUploadedFile("form_test.txt", b"Form test content")
        guidance = "Extract all entity names and their roles"
        
        form_data = {'guidance': guidance}
        form_files = {'document': document}
        
        form = DocumentUploadForm(form_data, form_files)
        assert form.is_valid(), f"Form errors: {form.errors}"
        
        # Save form (without committing to test the save method)
        session = form.save(commit=False)
        session.created_by = self.user
        session.save()
        
        # Verify guidance is stored in session_data
        assert session.session_data['guidance'] == guidance
    
    def test_form_handles_empty_guidance(self):
        """Test that form handles empty guidance correctly."""
        document = SimpleUploadedFile("empty_guide.pdf", b"PDF content")
        
        form_data = {'guidance': ''}
        form_files = {'document': document}
        
        form = DocumentUploadForm(form_data, form_files)
        assert form.is_valid()
        
        session = form.save(commit=False)
        session.created_by = self.user
        session.save()
        
        assert session.session_data['guidance'] == ''
    
    def test_form_validates_file_type(self):
        """Test that form validates file type correctly."""
        # Test valid file
        valid_document = SimpleUploadedFile("valid.txt", b"Valid content")
        form = DocumentUploadForm({}, {'document': valid_document})
        assert form.is_valid()
        
        # Test invalid file
        invalid_document = SimpleUploadedFile("invalid.exe", b"Invalid content")
        form = DocumentUploadForm({}, {'document': invalid_document})
        assert not form.is_valid()
        assert 'document' in form.errors
        assert 'Unsupported file type' in str(form.errors['document'])
    
    def test_form_without_document_is_invalid(self):
        """Test that form without document is invalid."""
        form = DocumentUploadForm({'guidance': 'Some guidance'}, {})
        assert not form.is_valid()
        assert 'document' in form.errors