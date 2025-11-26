"""
Integration tests for DocumentSource Django Admin.

Tests the admin interface configuration including:
- Custom form with entity ID validation
- Soft deletion interface
- Role-based permissions
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib import admin
from django.test import RequestFactory
from cases.models import DocumentSource, Case, CaseType
from cases.admin import DocumentSourceAdmin


User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = User.objects.create_user(
        username='testadmin',
        email='admin@test.com',
        password='test123'
    )
    group, _ = Group.objects.get_or_create(name='Admin')
    user.groups.add(group)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def moderator_user(db):
    """Create a moderator user."""
    user = User.objects.create_user(
        username='testmod',
        email='mod@test.com',
        password='test123'
    )
    group, _ = Group.objects.get_or_create(name='Moderator')
    user.groups.add(group)
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def contributor_user(db):
    """Create a contributor user."""
    user = User.objects.create_user(
        username='testcontrib',
        email='contrib@test.com',
        password='test123'
    )
    group, _ = Group.objects.get_or_create(name='Contributor')
    user.groups.add(group)
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def request_factory():
    """Create a request factory."""
    return RequestFactory()


@pytest.fixture
def document_source(db):
    """Create a test document source."""
    source = DocumentSource(
        title='Test Source',
        description='Test description',
        related_entity_ids=[]
    )
    source.save()
    return source


@pytest.fixture
def case_with_contributor(db, contributor_user):
    """Create a case with an assigned contributor."""
    case = Case.objects.create(
        title='Test Case',
        alleged_entities=['entity:person/test'],
        case_type=CaseType.CORRUPTION
    )
    case.contributors.add(contributor_user)
    return case


class TestDocumentSourceAdmin:
    """Test DocumentSource admin configuration."""
    
    def test_admin_is_registered(self, db):
        """Test that DocumentSource is registered in admin."""
        assert admin.site.is_registered(DocumentSource)
    
    def test_custom_form_is_used(self, db):
        """Test that custom form is configured."""
        admin_instance = admin.site._registry[DocumentSource]
        assert admin_instance.form.__name__ == 'DocumentSourceAdminForm'
    
    def test_fieldsets_configured(self, db):
        """Test that fieldsets are properly configured."""
        admin_instance = admin.site._registry[DocumentSource]
        assert len(admin_instance.fieldsets) == 4
        
        # Check fieldset names
        fieldset_names = [fs[0] for fs in admin_instance.fieldsets]
        assert 'Basic Information' in fieldset_names
        assert 'Relationships' in fieldset_names
        assert 'Status' in fieldset_names
        assert 'Metadata' in fieldset_names
    
    def test_list_display_configured(self, db):
        """Test that list display is properly configured."""
        admin_instance = admin.site._registry[DocumentSource]
        expected_fields = ['source_id', 'title', 'case', 'deletion_status', 'created_at']
        assert admin_instance.list_display == expected_fields
    
    def test_soft_delete_action_exists(self, db):
        """Test that soft delete action is available."""
        admin_instance = admin.site._registry[DocumentSource]
        assert hasattr(admin_instance, 'soft_delete_sources')
    
    def test_restore_action_exists(self, db):
        """Test that restore action is available."""
        admin_instance = admin.site._registry[DocumentSource]
        assert hasattr(admin_instance, 'restore_sources')
    
    def test_hard_delete_disabled(self, db, admin_user, request_factory, document_source):
        """Test that hard deletion is disabled."""
        admin_instance = admin.site._registry[DocumentSource]
        request = request_factory.get('/')
        request.user = admin_user
        
        # Hard delete should be disabled for everyone
        assert not admin_instance.has_delete_permission(request, document_source)
    
    def test_admin_can_change_source(self, db, admin_user, request_factory, document_source):
        """Test that admin can change sources."""
        admin_instance = admin.site._registry[DocumentSource]
        request = request_factory.get('/')
        request.user = admin_user
        
        assert admin_instance.has_change_permission(request, document_source)
    
    def test_moderator_can_change_source(self, db, moderator_user, request_factory, document_source):
        """Test that moderator can change sources."""
        admin_instance = admin.site._registry[DocumentSource]
        request = request_factory.get('/')
        request.user = moderator_user
        
        assert admin_instance.has_change_permission(request, document_source)
    
    def test_contributor_can_change_assigned_case_source(
        self, db, contributor_user, request_factory, case_with_contributor
    ):
        """Test that contributor can change sources for assigned cases."""
        # Create source linked to assigned case
        source = DocumentSource(
            title='Test Source',
            description='Test description',
            case=case_with_contributor,
            related_entity_ids=[]
        )
        source.save()
        
        admin_instance = admin.site._registry[DocumentSource]
        request = request_factory.get('/')
        request.user = contributor_user
        
        assert admin_instance.has_change_permission(request, source)
    
    def test_soft_deletion_preserves_record(self, db, document_source):
        """Test that soft deletion preserves the record in database."""
        source_id = document_source.id
        
        # Soft delete
        document_source.is_deleted = True
        document_source.save()
        
        # Should still exist in database
        assert DocumentSource.objects.filter(id=source_id).exists()
        
        # Verify is_deleted flag
        document_source.refresh_from_db()
        assert document_source.is_deleted is True
    
    def test_deletion_status_badge_for_active(self, db, document_source):
        """Test deletion status badge for active sources."""
        admin_instance = admin.site._registry[DocumentSource]
        badge_html = admin_instance.deletion_status(document_source)
        
        assert 'Active' in badge_html
        assert '#28a745' in badge_html  # Green color
    
    def test_deletion_status_badge_for_deleted(self, db, document_source):
        """Test deletion status badge for deleted sources."""
        document_source.is_deleted = True
        document_source.save()
        
        admin_instance = admin.site._registry[DocumentSource]
        badge_html = admin_instance.deletion_status(document_source)
        
        assert 'Deleted' in badge_html
        assert '#dc3545' in badge_html  # Red color


class TestDocumentSourceAdminForm:
    """Test DocumentSource admin form validation."""
    
    def test_form_validates_empty_title(self, db):
        """Test that form rejects empty title."""
        from cases.admin import DocumentSourceAdminForm
        
        form = DocumentSourceAdminForm(data={
            'title': '',
            'description': 'Valid description',
            'related_entity_ids': '[]',
        })
        
        assert not form.is_valid()
        assert 'title' in form.errors
    
    def test_form_validates_empty_description(self, db):
        """Test that form rejects empty description."""
        from cases.admin import DocumentSourceAdminForm
        
        form = DocumentSourceAdminForm(data={
            'title': 'Valid Title',
            'description': '',
            'related_entity_ids': '[]',
        })
        
        assert not form.is_valid()
        assert 'description' in form.errors
    
    def test_form_accepts_valid_data(self, db, document_source):
        """Test that form accepts valid data."""
        from cases.admin import DocumentSourceAdminForm
        
        # Use an existing instance to avoid source_id validation
        form = DocumentSourceAdminForm(
            instance=document_source,
            data={
                'source_id': document_source.source_id,
                'title': 'Valid Title',
                'description': 'Valid description',
                'related_entity_ids': '[]',
                'is_deleted': False,
            }
        )
        
        assert form.is_valid(), f"Form errors: {form.errors}"
