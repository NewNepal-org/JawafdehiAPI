from tests.conftest import create_case_with_entities, create_entities_from_ids
"""
End-to-End tests for Django Admin workflows.

Feature: accountability-platform-core
Tests complete admin workflows including case management, permissions, and versioning
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 5.1, 5.2, 5.3, 7.1, 7.3
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse
from django.core.exceptions import ValidationError

from cases.models import Case, CaseState, CaseType, DocumentSource
from cases.admin import CaseAdmin


User = get_user_model()


# ============================================================================
# Helper Functions
# ============================================================================

def create_user_with_role(username, email, role, password="testpass123"):
    """
    Create a user with the specified role.
    
    Creates the role group if it doesn't exist and assigns the user to it.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    
    # Create or get the role group
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    
    # Set staff status for Admin, Moderator, and Contributor
    if role in ['Admin', 'Moderator', 'Contributor']:
        user.is_staff = True
        user.save()
    
    # Set superuser status for Admin
    if role == 'Admin':
        user.is_superuser = True
        user.save()
    
    # Add necessary permissions for the role
    content_type = ContentType.objects.get_for_model(Case)
    user_content_type = ContentType.objects.get_for_model(User)
    
    # Get or create Case permissions
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_case',
        content_type=content_type,
        defaults={'name': 'Can view case'}
    )
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_case',
        content_type=content_type,
        defaults={'name': 'Can change case'}
    )
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_case',
        content_type=content_type,
        defaults={'name': 'Can add case'}
    )
    delete_perm, _ = Permission.objects.get_or_create(
        codename='delete_case',
        content_type=content_type,
        defaults={'name': 'Can delete case'}
    )
    
    # Get or create User permissions (for moderators to manage users)
    user_view_perm, _ = Permission.objects.get_or_create(
        codename='view_user',
        content_type=user_content_type,
        defaults={'name': 'Can view user'}
    )
    user_change_perm, _ = Permission.objects.get_or_create(
        codename='change_user',
        content_type=user_content_type,
        defaults={'name': 'Can change user'}
    )
    user_add_perm, _ = Permission.objects.get_or_create(
        codename='add_user',
        content_type=user_content_type,
        defaults={'name': 'Can add user'}
    )
    user_delete_perm, _ = Permission.objects.get_or_create(
        codename='delete_user',
        content_type=user_content_type,
        defaults={'name': 'Can delete user'}
    )
    
    # Assign permissions based on role
    if role in ['Admin', 'Moderator', 'Contributor']:
        user.user_permissions.add(view_perm, change_perm, add_perm, delete_perm)
    
    # Moderators and Admins can manage users
    if role in ['Admin', 'Moderator']:
        user.user_permissions.add(user_view_perm, user_change_perm, user_add_perm, user_delete_perm)
    
    return user


# ============================================================================
# E2E Test Class
# ============================================================================

@pytest.mark.django_db
class TestDjangoAdminWorkflows:
    """
    End-to-end tests for Django Admin workflows.
    
    These tests simulate complete user journeys through the Django Admin,
    testing the integration of case management, permissions, and versioning.
    """
    
    def setup_method(self):
        """Set up test data for each test."""
        # Create users with different roles
        self.admin = create_user_with_role('admin', 'admin@example.com', 'Admin')
        self.moderator = create_user_with_role('moderator', 'moderator@example.com', 'Moderator')
        self.contributor1 = create_user_with_role('contributor1', 'contributor1@example.com', 'Contributor')
        self.contributor2 = create_user_with_role('contributor2', 'contributor2@example.com', 'Contributor')
        
        # Create Django test client
        self.client = Client()

    
    def test_create_draft_edit_submit_review_publish_workflow(self):
        """
        E2E Test: Complete case lifecycle from creation to publication.
        
        Workflow:
        1. Contributor creates a draft case
        2. Contributor edits the draft
        3. Contributor submits for review (DRAFT → IN_REVIEW)
        4. Moderator reviews the case
        5. Moderator publishes the case (IN_REVIEW → PUBLISHED)
        
        Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2
        """
        # Step 1: Contributor creates a draft case
        case = create_case_with_entities(
            title="New Corruption Case",
            alleged_entities=["entity:person/test-official"],
            key_allegations=["Initial allegation"],
            case_type=CaseType.CORRUPTION,
            description="Initial draft description",
            state=CaseState.DRAFT
        )
        
        # Assign contributor to the case
        case.contributors.add(self.contributor1)
        case.save()
        
        # Verify initial state
        assert case.state == CaseState.DRAFT, \
            "New case should start in DRAFT state (Requirement 1.1)"
        assert case.version == 1, \
            "New case should start at version 1"
        
        # Step 2: Contributor edits the draft
        case.title = "Updated Corruption Case"
        case.key_allegations = ["Initial allegation", "Additional allegation"]
        case.description = "Updated draft description with more details"
        case.save()
        
        # Verify changes were saved
        case.refresh_from_db()
        assert case.title == "Updated Corruption Case"
        assert len(case.key_allegations) == 2
        assert case.state == CaseState.DRAFT, \
            "Case should remain in DRAFT state after editing"
        
        # Step 3: Contributor submits for review
        case.submit()
        
        # Verify state transition
        case.refresh_from_db()
        assert case.state == CaseState.IN_REVIEW, \
            "Case should transition to IN_REVIEW after submission (Requirement 1.3)"
        assert case.versionInfo is not None, \
            "versionInfo should be updated after submission"
        assert case.versionInfo.get('action') == 'submitted', \
            "versionInfo should record the submission action"
        
        # Step 4: Moderator reviews the case
        # Verify moderator can access the case
        admin_instance = CaseAdmin(Case, None)
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.moderator
        
        queryset = admin_instance.get_queryset(request)
        assert case in queryset, \
            "Moderator should be able to access all cases (Requirement 2.3)"
        
        has_permission = admin_instance.has_change_permission(request, case)
        assert has_permission, \
            "Moderator should have permission to change the case"
        
        # Step 5: Moderator publishes the case
        case.publish()
        
        # Verify publication
        case.refresh_from_db()
        assert case.state == CaseState.PUBLISHED, \
            "Case should transition to PUBLISHED after moderator approval (Requirement 2.1, 2.2)"
        assert case.versionInfo.get('action') == 'published', \
            "versionInfo should record the publication action (Requirement 2.4)"

    
    def test_contributor_assignment_and_access_restrictions(self):
        """
        E2E Test: Verify contributor assignment restricts access correctly.
        
        Workflow:
        1. Admin creates a case and assigns contributor1
        2. Contributor1 can access and edit the case
        3. Contributor2 cannot access the case
        4. Admin assigns contributor2 to the case
        5. Contributor2 can now access the case
        
        Validates: Requirements 3.1, 3.2, 5.2
        """
        # Step 1: Admin creates a case and assigns contributor1
        case = create_case_with_entities(
            title="Assigned Case",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.DRAFT
        )
        case.contributors.add(self.contributor1)
        case.save()
        
        # Step 2: Verify contributor1 can access the case
        admin_instance = CaseAdmin(Case, None)
        from django.test import RequestFactory
        factory = RequestFactory()
        
        request1 = factory.get('/')
        request1.user = self.contributor1
        
        queryset1 = admin_instance.get_queryset(request1)
        assert case in queryset1, \
            "Contributor1 should see assigned case in queryset (Requirement 3.1)"
        
        has_permission1 = admin_instance.has_change_permission(request1, case)
        assert has_permission1, \
            "Contributor1 should have permission to change assigned case"
        
        # Contributor1 can edit the case
        case.title = "Updated by Contributor1"
        case.save()
        case.refresh_from_db()
        assert case.title == "Updated by Contributor1"
        
        # Step 3: Verify contributor2 cannot access the case
        request2 = factory.get('/')
        request2.user = self.contributor2
        
        queryset2 = admin_instance.get_queryset(request2)
        assert case not in queryset2, \
            "Contributor2 should NOT see unassigned case in queryset (Requirement 3.2)"
        
        has_permission2 = admin_instance.has_change_permission(request2, case)
        assert not has_permission2, \
            "Contributor2 should NOT have permission to change unassigned case"
        
        # Step 4: Admin assigns contributor2 to the case
        case.contributors.add(self.contributor2)
        case.save()
        
        # Step 5: Verify contributor2 can now access the case
        queryset2_after = admin_instance.get_queryset(request2)
        assert case in queryset2_after, \
            "Contributor2 should now see the case after assignment"
        
        has_permission2_after = admin_instance.has_change_permission(request2, case)
        assert has_permission2_after, \
            "Contributor2 should now have permission to change the case"

    
    def test_contributor_can_see_own_created_case_in_list(self):
        """
        E2E Test: Verify contributor can see their own created case in list view.
        
        Workflow:
        1. Contributor creates a new draft case via admin
        2. Verify creator is automatically added to contributors
        3. Contributor performs list query
        4. Verify the created case appears in their list
        5. Verify another contributor cannot see the case
        
        Validates: Requirements 3.1, 3.2
        """
        # Step 1: Contributor creates a new draft case via admin
        admin_instance = CaseAdmin(Case, None)
        from django.test import RequestFactory
        factory = RequestFactory()
        
        request_contrib1 = factory.get('/')
        request_contrib1.user = self.contributor1
        
        case = create_case_with_entities(
            title="Contributor's New Case",
            alleged_entities=["entity:person/test-official"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Case created by contributor1",
            state=CaseState.DRAFT
        )
        
        # Simulate admin save (which should auto-add creator to contributors)
        admin_instance.save_model(request_contrib1, case, None, change=False)
        
        # Simulate save_related (which adds creator to contributors)
        class DummyForm:
            instance = case
            def save_m2m(self):
                pass
        admin_instance.save_related(request_contrib1, DummyForm(), [], change=False)
        
        # Step 2: Verify creator is automatically added to contributors
        assert self.contributor1 in case.contributors.all(), \
            "Creator should be automatically added to contributors when creating a case"
        
        # Step 3: Contributor performs list query
        queryset = admin_instance.get_queryset(request_contrib1)
        
        # Step 4: Verify the created case appears in their list
        assert case in queryset, \
            "Contributor should see their own created case in list view (Requirement 3.1)"
        
        # Verify contributor has access to view and edit
        has_view_permission = admin_instance.has_view_permission(request_contrib1, case)
        assert has_view_permission, \
            "Contributor should have view permission for their own case"
        
        has_change_permission = admin_instance.has_change_permission(request_contrib1, case)
        assert has_change_permission, \
            "Contributor should have change permission for their own case"
        
        # Step 5: Verify another contributor cannot see the case
        request_contrib2 = factory.get('/')
        request_contrib2.user = self.contributor2
        
        queryset2 = admin_instance.get_queryset(request_contrib2)
        assert case not in queryset2, \
            "Other contributors should NOT see unassigned cases in list view (Requirement 3.2)"
        
        has_view_permission2 = admin_instance.has_view_permission(request_contrib2, case)
        assert not has_view_permission2, \
            "Other contributors should NOT have view permission for unassigned cases"

    
    def test_state_transitions_with_validation(self):
        """
        E2E Test: Verify state transitions are validated correctly.
        
        Workflow:
        1. Create a draft case with minimal data
        2. Attempt to transition to IN_REVIEW without required fields (should fail)
        3. Add required fields
        4. Successfully transition to IN_REVIEW
        5. Contributor attempts to publish (should fail)
        6. Moderator successfully publishes
        
        Validates: Requirements 1.2, 1.5, 2.1
        """
        # Step 1: Create a draft case with minimal data
        case = create_case_with_entities(
            title="Minimal Draft",
            alleged_entities=["entity:person/test"],
            case_type=CaseType.CORRUPTION,
            state=CaseState.DRAFT
        )
        case.contributors.add(self.contributor1)
        case.save()
        
        # Step 2: Attempt to transition to IN_REVIEW without required fields
        case.state = CaseState.IN_REVIEW
        
        with pytest.raises(ValidationError) as exc_info:
            case.validate()
        
        # Verify validation error mentions missing fields
        error_dict = exc_info.value.message_dict
        assert 'key_allegations' in error_dict or 'description' in error_dict, \
            "Validation should fail for IN_REVIEW without required fields (Requirement 1.2)"
        
        # Reset state
        case.state = CaseState.DRAFT
        case.save()
        
        # Step 3: Add required fields
        case.key_allegations = ["Complete allegation statement"]
        case.description = "Complete description with sufficient detail"
        case.save()
        
        # Step 4: Successfully transition to IN_REVIEW
        case.submit()
        case.refresh_from_db()
        assert case.state == CaseState.IN_REVIEW, \
            "Case should transition to IN_REVIEW with complete data"
        
        # Step 5: Contributor attempts to publish (should fail)
        admin_instance = CaseAdmin(Case, None)
        from django.test import RequestFactory
        factory = RequestFactory()
        
        request_contrib = factory.get('/')
        request_contrib.user = self.contributor1
        
        case.state = CaseState.PUBLISHED
        
        with pytest.raises(ValidationError) as exc_info:
            admin_instance.save_model(request_contrib, case, None, change=True)
        
        # Verify error message mentions contributor restrictions
        error_message = str(exc_info.value)
        assert "Contributors can only transition between DRAFT and IN_REVIEW" in error_message, \
            "Contributor should not be able to publish (Requirement 1.5)"
        
        # Reset state
        case.state = CaseState.IN_REVIEW
        case.save()
        
        # Step 6: Moderator successfully publishes
        request_mod = factory.get('/')
        request_mod.user = self.moderator
        
        case.state = CaseState.PUBLISHED
        admin_instance.save_model(request_mod, case, None, change=True)
        
        case.refresh_from_db()
        assert case.state == CaseState.PUBLISHED, \
            "Moderator should be able to publish the case (Requirement 2.1)"

    
    def test_version_creation_when_editing_published_cases(self):
        """
        E2E Test: Verify editing a published case creates a new draft version.
        
        Workflow:
        1. Create and publish a case (version 1)
        2. Create a draft from the published case
        3. Verify new draft has incremented version
        4. Edit the draft
        5. Publish the draft (version 2)
        6. Verify both versions exist in database
        7. Verify original published version is preserved
        
        Validates: Requirements 1.4, 7.1
        """
        # Step 1: Create and publish a case (version 1)
        case_v1 = create_case_with_entities(
            title="Original Case Title",
            alleged_entities=["entity:person/original"],
            key_allegations=["Original allegation"],
            case_type=CaseType.CORRUPTION,
            description="Original description",
            state=CaseState.PUBLISHED,
            version=1
        )
        
        original_case_id = case_v1.case_id
        original_title = case_v1.title
        
        # Step 2: Create a draft from the published case
        case_v2_draft = case_v1.create_draft()
        
        # Step 3: Verify new draft has incremented version
        assert case_v2_draft.case_id == original_case_id, \
            "Draft should have same case_id as original"
        assert case_v2_draft.version == 2, \
            "Draft should have incremented version (Requirement 1.4)"
        assert case_v2_draft.state == CaseState.DRAFT, \
            "New version should start in DRAFT state"
        assert case_v2_draft.versionInfo.get('action') == 'draft_created', \
            "versionInfo should record draft creation"
        assert case_v2_draft.versionInfo.get('source_version') == 1, \
            "versionInfo should reference source version"
        
        # Step 4: Edit the draft
        case_v2_draft.title = "Updated Case Title"
        case_v2_draft.key_allegations = ["Original allegation", "New allegation"]
        case_v2_draft.description = "Updated description with new information"
        case_v2_draft.save()
        
        # Step 5: Publish the draft (version 2)
        case_v2_draft.state = CaseState.IN_REVIEW
        case_v2_draft.save()
        case_v2_draft.publish()
        
        case_v2_draft.refresh_from_db()
        assert case_v2_draft.state == CaseState.PUBLISHED
        assert case_v2_draft.version == 2
        
        # Step 6: Verify both versions exist in database
        all_versions = Case.objects.filter(case_id=original_case_id).order_by('version')
        assert all_versions.count() == 2, \
            "Both versions should exist in database (Requirement 7.1)"
        
        # Step 7: Verify original published version is preserved
        case_v1.refresh_from_db()
        assert case_v1.title == original_title, \
            "Original version should be preserved unchanged (Requirement 1.4)"
        assert case_v1.version == 1
        assert case_v1.state == CaseState.PUBLISHED
        
        # Verify the versions are distinct records
        assert case_v1.id != case_v2_draft.id, \
            "Versions should be separate database records"

    
    def test_soft_deletion(self):
        """
        E2E Test: Verify soft deletion sets state to CLOSED and preserves data.
        
        Workflow:
        1. Create a published case
        2. Soft delete the case (using delete() method)
        3. Verify state is set to CLOSED
        4. Verify case still exists in database
        5. Verify versionInfo records the deletion
        6. Verify case is not visible in public API
        
        Validates: Requirements 7.3
        """
        # Step 1: Create a published case
        case = create_case_with_entities(
            title="Case to be Deleted",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.PUBLISHED,
            version=1
        )
        
        case_id = case.id
        case_case_id = case.case_id
        
        # Step 2: Soft delete the case
        result = case.delete()
        
        # Verify delete() returns expected tuple
        assert result == (0, {'cases.Case': 0}), \
            "Soft delete should report 0 actual deletions"
        
        # Step 3: Verify state is set to CLOSED
        case.refresh_from_db()
        assert case.state == CaseState.CLOSED, \
            "Soft delete should set state to CLOSED (Requirement 7.3)"
        
        # Step 4: Verify case still exists in database
        deleted_case = Case.objects.get(id=case_id)
        assert deleted_case is not None, \
            "Case should still exist in database after soft delete"
        assert deleted_case.title == "Case to be Deleted", \
            "Case data should be preserved"
        
        # Step 5: Verify versionInfo records the deletion
        assert deleted_case.versionInfo is not None
        assert deleted_case.versionInfo.get('action') == 'deleted', \
            "versionInfo should record the deletion action"
        assert 'datetime' in deleted_case.versionInfo, \
            "versionInfo should include deletion timestamp"
        
        # Step 6: Verify case is not visible in public API
        # (This would be tested by checking the API queryset filters)
        # For now, we verify the state is CLOSED which the API filters out
        assert deleted_case.state == CaseState.CLOSED
        
        # Verify we can query all cases including closed ones
        all_cases = Case.objects.all()
        assert deleted_case in all_cases, \
            "Closed case should be queryable with all()"
        
        # Verify filtering by state works
        closed_cases = Case.objects.filter(state=CaseState.CLOSED)
        assert deleted_case in closed_cases, \
            "Should be able to filter for closed cases"

    
    def test_admin_full_access_workflow(self):
        """
        E2E Test: Verify Admin has full access to all cases and users.
        
        Workflow:
        1. Create cases assigned to different contributors
        2. Verify Admin can access all cases
        3. Verify Admin can transition cases to any state
        4. Verify Admin can manage moderators
        
        Validates: Requirements 5.1
        """
        # Step 1: Create cases assigned to different contributors
        case1 = create_case_with_entities(
            title="Case for Contributor 1",
            alleged_entities=["entity:person/test1"],
            key_allegations=["Allegation 1"],
            case_type=CaseType.CORRUPTION,
            description="Description 1",
            state=CaseState.DRAFT
        )
        case1.contributors.add(self.contributor1)
        
        case2 = create_case_with_entities(
            title="Case for Contributor 2",
            alleged_entities=["entity:person/test2"],
            key_allegations=["Allegation 2"],
            case_type=CaseType.PROMISES,
            description="Description 2",
            state=CaseState.IN_REVIEW
        )
        case2.contributors.add(self.contributor2)
        
        # Step 2: Verify Admin can access all cases
        admin_instance = CaseAdmin(Case, None)
        from django.test import RequestFactory
        factory = RequestFactory()
        
        request_admin = factory.get('/')
        request_admin.user = self.admin
        
        queryset = admin_instance.get_queryset(request_admin)
        assert case1 in queryset, \
            "Admin should see case assigned to contributor1"
        assert case2 in queryset, \
            "Admin should see case assigned to contributor2"
        
        # Verify Admin has change permission for all cases
        assert admin_instance.has_change_permission(request_admin, case1), \
            "Admin should have permission to change any case (Requirement 5.1)"
        assert admin_instance.has_change_permission(request_admin, case2), \
            "Admin should have permission to change any case"
        
        # Step 3: Verify Admin can transition cases to any state
        case1.state = CaseState.PUBLISHED
        admin_instance.save_model(request_admin, case1, None, change=True)
        case1.refresh_from_db()
        assert case1.state == CaseState.PUBLISHED, \
            "Admin should be able to publish cases"
        
        case2.state = CaseState.CLOSED
        admin_instance.save_model(request_admin, case2, None, change=True)
        case2.refresh_from_db()
        assert case2.state == CaseState.CLOSED, \
            "Admin should be able to close cases"
        
        # Step 4: Verify Admin can manage moderators
        # Admin is a superuser, so they can manage all users including moderators
        assert self.admin.is_superuser, \
            "Admin should be a superuser"
        
        # Verify admin can access moderator user
        from cases.admin import CustomUserAdmin
        user_admin = CustomUserAdmin(User, None)
        
        user_queryset = user_admin.get_queryset(request_admin)
        assert self.moderator in user_queryset, \
            "Admin should be able to see moderator users"
        
        assert user_admin.has_change_permission(request_admin, self.moderator), \
            "Admin should be able to change moderator users"

    
    def test_moderator_cannot_manage_other_moderators(self):
        """
        E2E Test: Verify Moderators cannot manage other Moderators.
        
        Workflow:
        1. Create two moderator users
        2. Verify moderator1 cannot see moderator2 in user queryset
        3. Verify moderator1 cannot change moderator2
        4. Verify moderator can manage contributors
        
        Validates: Requirements 5.3
        """
        # Step 1: Two moderators already exist (self.moderator and we'll create another)
        moderator2 = create_user_with_role('moderator2', 'moderator2@example.com', 'Moderator')
        
        # Step 2: Verify moderator1 cannot see moderator2 in user queryset
        from cases.admin import CustomUserAdmin
        from django.test import RequestFactory
        
        user_admin = CustomUserAdmin(User, None)
        factory = RequestFactory()
        
        request_mod = factory.get('/')
        request_mod.user = self.moderator
        
        user_queryset = user_admin.get_queryset(request_mod)
        
        # Moderator should not see other moderators in queryset
        assert moderator2 not in user_queryset, \
            "Moderator should NOT see other moderators in queryset (Requirement 5.3)"
        assert self.moderator not in user_queryset, \
            "Moderator should NOT see themselves in queryset"
        
        # Step 3: Verify moderator1 cannot change moderator2
        has_permission = user_admin.has_change_permission(request_mod, moderator2)
        assert not has_permission, \
            "Moderator should NOT have permission to change other moderators"
        
        # Verify moderator cannot delete other moderators
        has_delete_permission = user_admin.has_delete_permission(request_mod, moderator2)
        assert not has_delete_permission, \
            "Moderator should NOT have permission to delete other moderators"
        
        # Step 4: Verify moderator can manage contributors
        assert self.contributor1 in user_queryset, \
            "Moderator should be able to see contributors"
        
        has_contrib_permission = user_admin.has_change_permission(request_mod, self.contributor1)
        assert has_contrib_permission, \
            "Moderator should have permission to change contributors"

    
    def test_complete_multi_version_workflow(self):
        """
        E2E Test: Complete workflow with multiple versions and state transitions.
        
        Workflow:
        1. Contributor creates draft v1
        2. Contributor submits v1 for review
        3. Moderator publishes v1
        4. Contributor creates draft v2 from published v1
        5. Contributor edits and submits v2
        6. Moderator publishes v2
        7. Verify version history is complete
        
        Validates: Requirements 1.1, 1.3, 1.4, 2.1, 2.2, 7.1, 7.2
        """
        # Step 1: Contributor creates draft v1
        case_v1 = create_case_with_entities(
            title="Multi-Version Case v1",
            alleged_entities=["entity:person/test"],
            key_allegations=["Initial allegation"],
            case_type=CaseType.CORRUPTION,
            description="Initial version description",
            state=CaseState.DRAFT
        )
        case_v1.contributors.add(self.contributor1)
        case_v1.save()
        
        assert case_v1.state == CaseState.DRAFT
        assert case_v1.version == 1
        
        case_id = case_v1.case_id
        
        # Step 2: Contributor submits v1 for review
        case_v1.submit()
        case_v1.refresh_from_db()
        
        assert case_v1.state == CaseState.IN_REVIEW
        assert case_v1.versionInfo.get('action') == 'submitted'
        
        # Step 3: Moderator publishes v1
        case_v1.publish()
        case_v1.refresh_from_db()
        
        assert case_v1.state == CaseState.PUBLISHED
        assert case_v1.versionInfo.get('action') == 'published'
        
        # Step 4: Contributor creates draft v2 from published v1
        case_v2 = case_v1.create_draft()
        
        assert case_v2.case_id == case_id
        assert case_v2.version == 2
        assert case_v2.state == CaseState.DRAFT
        assert case_v2.versionInfo.get('action') == 'draft_created'
        assert case_v2.versionInfo.get('source_version') == 1
        
        # Step 5: Contributor edits and submits v2
        case_v2.title = "Multi-Version Case v2 - Updated"
        case_v2.key_allegations = ["Initial allegation", "Updated allegation"]
        case_v2.description = "Updated version with new information"
        case_v2.save()
        
        case_v2.submit()
        case_v2.refresh_from_db()
        
        assert case_v2.state == CaseState.IN_REVIEW
        
        # Step 6: Moderator publishes v2
        case_v2.publish()
        case_v2.refresh_from_db()
        
        assert case_v2.state == CaseState.PUBLISHED
        assert case_v2.version == 2
        
        # Step 7: Verify version history is complete
        all_versions = Case.objects.filter(case_id=case_id).order_by('version')
        assert all_versions.count() == 2, \
            "Should have 2 versions in database"
        
        # Verify v1 is still preserved
        case_v1.refresh_from_db()
        assert case_v1.title == "Multi-Version Case v1"
        assert case_v1.version == 1
        assert case_v1.state == CaseState.PUBLISHED
        
        # Verify v2 has updated content
        assert case_v2.title == "Multi-Version Case v2 - Updated"
        assert case_v2.version == 2
        assert case_v2.state == CaseState.PUBLISHED
        
        # Verify both versions have complete versionInfo
        assert case_v1.versionInfo is not None
        assert case_v2.versionInfo is not None
        assert 'datetime' in case_v1.versionInfo
        assert 'datetime' in case_v2.versionInfo

    
    def test_contributor_state_transition_restrictions(self):
        """
        E2E Test: Verify contributors can only transition between DRAFT and IN_REVIEW.
        
        Workflow:
        1. Contributor creates a draft
        2. Contributor transitions DRAFT → IN_REVIEW (allowed)
        3. Contributor transitions IN_REVIEW → DRAFT (allowed)
        4. Contributor attempts DRAFT → PUBLISHED (should fail)
        5. Contributor attempts IN_REVIEW → CLOSED (should fail)
        
        Validates: Requirements 1.5
        """
        # Step 1: Contributor creates a draft
        case = create_case_with_entities(
            title="State Transition Test",
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            case_type=CaseType.CORRUPTION,
            description="Test description",
            state=CaseState.DRAFT
        )
        case.contributors.add(self.contributor1)
        case.save()
        
        admin_instance = CaseAdmin(Case, None)
        from django.test import RequestFactory
        factory = RequestFactory()
        
        request_contrib = factory.get('/')
        request_contrib.user = self.contributor1
        
        # Step 2: Contributor transitions DRAFT → IN_REVIEW (allowed)
        case.state = CaseState.IN_REVIEW
        admin_instance.save_model(request_contrib, case, None, change=True)
        
        case.refresh_from_db()
        assert case.state == CaseState.IN_REVIEW, \
            "Contributor should be able to transition DRAFT → IN_REVIEW"
        
        # Step 3: Contributor transitions IN_REVIEW → DRAFT (allowed)
        case.state = CaseState.DRAFT
        admin_instance.save_model(request_contrib, case, None, change=True)
        
        case.refresh_from_db()
        assert case.state == CaseState.DRAFT, \
            "Contributor should be able to transition IN_REVIEW → DRAFT"
        
        # Step 4: Contributor attempts DRAFT → PUBLISHED (should fail)
        case.state = CaseState.PUBLISHED
        
        with pytest.raises(ValidationError) as exc_info:
            admin_instance.save_model(request_contrib, case, None, change=True)
        
        error_message = str(exc_info.value)
        assert "Contributors can only transition between DRAFT and IN_REVIEW" in error_message, \
            "Contributor should NOT be able to transition to PUBLISHED (Requirement 1.5)"
        
        # Reset state
        case.state = CaseState.DRAFT
        case.save()
        
        # Transition to IN_REVIEW for next test
        case.state = CaseState.IN_REVIEW
        admin_instance.save_model(request_contrib, case, None, change=True)
        case.refresh_from_db()
        
        # Step 5: Contributor attempts IN_REVIEW → CLOSED (should fail)
        case.state = CaseState.CLOSED
        
        with pytest.raises(ValidationError) as exc_info:
            admin_instance.save_model(request_contrib, case, None, change=True)
        
        error_message = str(exc_info.value)
        assert "Contributors can only transition between DRAFT and IN_REVIEW" in error_message, \
            "Contributor should NOT be able to transition to CLOSED"
    
    def test_document_source_soft_deletion(self):
        """
        E2E Test: Verify DocumentSource soft deletion preserves data.
        
        Workflow:
        1. Create a document source
        2. Mark it as deleted (is_deleted=True)
        3. Verify source still exists in database
        4. Verify source is marked as deleted
        
        Validates: Requirements 4.2
        """
        # Step 1: Create a document source
        source = DocumentSource(
            title="Test Source",
            description="Test source description"
        )
        source.save()
        source.related_entities.set(create_entities_from_ids(["entity:person/test"]))
        
        source_id = source.id
        source_source_id = source.source_id
        
        # Step 2: Mark it as deleted
        source.is_deleted = True
        source.save()
        
        # Step 3: Verify source still exists in database
        deleted_source = DocumentSource.objects.get(id=source_id)
        assert deleted_source is not None, \
            "Source should still exist in database after soft delete"
        
        # Step 4: Verify source is marked as deleted
        assert deleted_source.is_deleted is True, \
            "Source should be marked as deleted"
        assert deleted_source.title == "Test Source", \
            "Source data should be preserved"
        assert deleted_source.source_id == source_source_id, \
            "Source ID should be preserved"
        
        # Verify we can query all sources including deleted ones
        all_sources = DocumentSource.objects.all()
        assert deleted_source in all_sources, \
            "Deleted source should be queryable with all()"
        
        # Verify filtering by is_deleted works
        deleted_sources = DocumentSource.objects.filter(is_deleted=True)
        assert deleted_source in deleted_sources, \
            "Should be able to filter for deleted sources"
        
        active_sources = DocumentSource.objects.filter(is_deleted=False)
        assert deleted_source not in active_sources, \
            "Deleted source should not appear in active sources filter"
    
    def test_contributor_login_create_minimal_case_and_view_workflow(self):
        """
        E2E Test: Contributor logs in, creates a minimal case, and sees it in their list.
        
        Workflow:
        1. Contributor logs into Django Admin
        2. Contributor creates a new case with only title and case type
        3. Verify case is created successfully in DRAFT state
        4. Verify creator is automatically assigned as contributor
        5. Contributor views their case list
        6. Verify the new case appears in their list
        7. Contributor can access and view the case details
        
        Validates: Requirements 1.1, 3.1, 3.2
        """
        # Step 1: Contributor logs into Django Admin
        login_success = self.client.login(
            username='contributor1',
            password='testpass123'
        )
        assert login_success, "Contributor should be able to log in"
        
        # Verify contributor can access admin
        response = self.client.get('/admin/')
        assert response.status_code == 200, \
            "Contributor should be able to access admin interface"
        
        # Step 2: Contributor creates a new case with minimal data (title + case type)
        admin_instance = CaseAdmin(Case, None)
        from django.test import RequestFactory
        factory = RequestFactory()
        
        request_contrib = factory.post('/admin/cases/case/add/')
        request_contrib.user = self.contributor1
        
        # Create minimal case - only title and case type required
        minimal_case = create_case_with_entities(
            title="Minimal Case - Quick Start",
            case_type=CaseType.CORRUPTION,
            alleged_entities=["entity:person/placeholder"]  # Required field
        )
        
        # Step 3: Save via admin (simulating form submission)
        admin_instance.save_model(request_contrib, minimal_case, None, change=False)
        
        # Simulate save_related (which adds creator to contributors)
        class DummyForm:
            instance = minimal_case
            def save_m2m(self):
                pass
        admin_instance.save_related(request_contrib, DummyForm(), [], change=False)
        
        # Verify case is created successfully
        assert minimal_case.id is not None, \
            "Case should be saved to database"
        assert minimal_case.state == CaseState.DRAFT, \
            "New case should start in DRAFT state (Requirement 1.1)"
        assert minimal_case.version == 1, \
            "New case should start at version 1"
        
        # Step 4: Verify creator is automatically assigned as contributor
        minimal_case.refresh_from_db()
        assert self.contributor1 in minimal_case.contributors.all(), \
            "Creator should be automatically assigned as contributor"
        
        # Step 5: Contributor views their case list
        request_list = factory.get('/admin/cases/case/')
        request_list.user = self.contributor1
        
        queryset = admin_instance.get_queryset(request_list)
        
        # Step 6: Verify the new case appears in their list
        assert minimal_case in queryset, \
            "Contributor should see their newly created case in list (Requirement 3.1)"
        
        # Verify case count
        contributor_cases = queryset.filter(contributors=self.contributor1)
        assert contributor_cases.count() >= 1, \
            "Contributor should have at least one case assigned"
        
        # Step 7: Contributor can access and view the case details
        has_view_permission = admin_instance.has_view_permission(
            request_list,
            minimal_case
        )
        assert has_view_permission, \
            "Contributor should have view permission for their own case"
        
        has_change_permission = admin_instance.has_change_permission(
            request_list,
            minimal_case
        )
        assert has_change_permission, \
            "Contributor should have change permission for their own case"
        
        # Verify case details are accessible
        response = self.client.get(f'/admin/cases/case/{minimal_case.id}/change/')
        assert response.status_code == 200, \
            "Contributor should be able to access case detail page"
        
        # Verify other contributor cannot see this case
        request_other = factory.get('/admin/cases/case/')
        request_other.user = self.contributor2
        
        queryset_other = admin_instance.get_queryset(request_other)
        assert minimal_case not in queryset_other, \
            "Other contributors should NOT see unassigned cases (Requirement 3.2)"
        
        has_view_permission_other = admin_instance.has_view_permission(
            request_other,
            minimal_case
        )
        assert not has_view_permission_other, \
            "Other contributors should NOT have view permission for unassigned cases"
    
    def test_new_case_must_be_draft_state(self):
        """
        E2E Test: Verify that new cases can only be created in DRAFT state.
        
        Workflow:
        1. Attempt to create a new case with state=PUBLISHED (should fail)
        2. Attempt to create a new case with state=IN_REVIEW (should fail)
        3. Attempt to create a new case with state=CLOSED (should fail)
        4. Create a new case with state=DRAFT (should succeed)
        5. Verify case is created successfully in DRAFT state
        
        Validates: Requirements 1.1
        """
        admin_instance = CaseAdmin(Case, None)
        from django.test import RequestFactory
        factory = RequestFactory()
        
        request_contrib = factory.post('/admin/cases/case/add/')
        request_contrib.user = self.contributor1
        
        # Step 1: Attempt to create a new case with state=PUBLISHED (should fail)
        case_published = create_case_with_entities(
            title="New Case - Published State",
            case_type=CaseType.CORRUPTION,
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            description="Test description",
            state=CaseState.PUBLISHED
        )
        
        with pytest.raises(ValidationError) as exc_info:
            admin_instance.save_model(request_contrib, case_published, None, change=False)
        
        error_message = str(exc_info.value)
        assert "New cases must be created in DRAFT state" in error_message, \
            "Should not allow creating new case with PUBLISHED state (Requirement 1.1)"
        
        # Step 2: Attempt to create a new case with state=IN_REVIEW (should fail)
        case_in_review = create_case_with_entities(
            title="New Case - In Review State",
            case_type=CaseType.CORRUPTION,
            alleged_entities=["entity:person/test"],
            key_allegations=["Test allegation"],
            description="Test description",
            state=CaseState.IN_REVIEW
        )
        
        with pytest.raises(ValidationError) as exc_info:
            admin_instance.save_model(request_contrib, case_in_review, None, change=False)
        
        error_message = str(exc_info.value)
        assert "New cases must be created in DRAFT state" in error_message, \
            "Should not allow creating new case with IN_REVIEW state"
        
        # Step 3: Attempt to create a new case with state=CLOSED (should fail)
        case_closed = create_case_with_entities(
            title="New Case - Closed State",
            case_type=CaseType.CORRUPTION,
            alleged_entities=["entity:person/test"],
            state=CaseState.CLOSED
        )
        
        with pytest.raises(ValidationError) as exc_info:
            admin_instance.save_model(request_contrib, case_closed, None, change=False)
        
        error_message = str(exc_info.value)
        assert "New cases must be created in DRAFT state" in error_message, \
            "Should not allow creating new case with CLOSED state"
        
        # Step 4: Create a new case with state=DRAFT (should succeed)
        case_draft = create_case_with_entities(
            title="New Case - Draft State",
            case_type=CaseType.CORRUPTION,
            alleged_entities=["entity:person/test"]
        )
        
        # Should not raise any exception
        admin_instance.save_model(request_contrib, case_draft, None, change=False)
        
        # Step 5: Verify case is created successfully in DRAFT state
        case_draft.refresh_from_db()
        assert case_draft.id is not None, \
            "Case should be saved to database"
        assert case_draft.state == CaseState.DRAFT, \
            "New case should be in DRAFT state (Requirement 1.1)"
        assert case_draft.version == 1, \
            "New case should start at version 1"
    
    def test_admin_entity_id_validation_on_create(self):
        """
        E2E Test: Verify entity ID validation in admin panel when creating a case.
        
        Tests that the admin form properly validates entity IDs using the
        MultiEntityIDField widget which calls NES validate_entity_id().
        
        Workflow:
        1. Test invalid entity ID format (missing 'entity:' prefix)
        2. Test invalid entity type (unsupported type)
        3. Test invalid slug format
        4. Test empty entity ID
        5. Test valid entity IDs (person, organization, location)
        6. Test mixed valid and invalid entity IDs
        
        Validates: Entity ID validation in admin panel
        """
        from cases.widgets import MultiEntityIDField
        
        # Test the field directly to isolate entity ID validation
        field = MultiEntityIDField(required=True)
        
        # Step 1: Test invalid entity ID format (missing 'entity:' prefix)
        with pytest.raises(ValidationError) as exc_info:
            field.clean('["invalid-format"]')
        
        error_message = str(exc_info.value)
        assert 'Invalid entity ID format' in error_message, \
            f"Error should mention invalid format. Got: {error_message}"
        
        # Step 2: Test invalid entity type (unsupported type)
        with pytest.raises(ValidationError) as exc_info:
            field.clean('["entity:invalid-type/test-slug"]')
        
        error_message = str(exc_info.value)
        assert 'entity type' in error_message.lower() or 'unsupported' in error_message.lower(), \
            f"Error should mention invalid entity type. Got: {error_message}"
        
        # Step 3: Test invalid slug format (contains invalid characters)
        with pytest.raises(ValidationError) as exc_info:
            field.clean('["entity:person/Invalid Slug With Spaces"]')
        
        error_message = str(exc_info.value)
        assert 'slug' in error_message.lower() or 'format' in error_message.lower(), \
            f"Error should mention invalid slug format. Got: {error_message}"
        
        # Step 4: Test empty entity ID
        with pytest.raises(ValidationError) as exc_info:
            field.clean('[""]')
        
        error_message = str(exc_info.value)
        assert 'Invalid entity ID format' in error_message or 'empty' in error_message.lower(), \
            f"Error should mention empty entity ID. Got: {error_message}"
        
        # Step 5: Test valid entity IDs
        # Valid person entity
        result = field.clean('["entity:person/john-doe"]')
        assert result == ["entity:person/john-doe"], \
            "Should accept valid person entity ID"
        
        # Valid organization entity
        result = field.clean('["entity:organization/test-org"]')
        assert result == ["entity:organization/test-org"], \
            "Should accept valid organization entity ID"
        
        # Valid location entity
        result = field.clean('["entity:location/kathmandu"]')
        assert result == ["entity:location/kathmandu"], \
            "Should accept valid location entity ID"
        
        # Multiple valid entity IDs
        result = field.clean('["entity:person/jane-doe", "entity:organization/ministry", "entity:location/district"]')
        assert len(result) == 3, \
            "Should accept multiple valid entity IDs"
        assert "entity:person/jane-doe" in result
        assert "entity:organization/ministry" in result
        assert "entity:location/district" in result
        
        # Step 6: Test mixed valid and invalid entity IDs
        with pytest.raises(ValidationError) as exc_info:
            field.clean('["entity:person/valid-person", "invalid-format"]')
        
        error_message = str(exc_info.value)
        assert 'Invalid entity ID format' in error_message, \
            "Should reject when mixing valid and invalid entity IDs"
    
    def test_admin_entity_id_validation_on_update(self):
        """
        E2E Test: Verify entity ID validation when updating an existing case.
        
        Workflow:
        1. Create a case with valid entity IDs
        2. Attempt to update with invalid entity ID via model
        3. Verify validation error is raised
        4. Update with valid entity IDs
        5. Verify update succeeds
        
        Validates: Entity ID validation on case updates
        """
        # Step 1: Create a case with valid entity IDs
        case = create_case_with_entities(
            title="Original Case",
            case_type=CaseType.CORRUPTION,
            alleged_entities=["entity:person/original-person"],
            state=CaseState.DRAFT
        )
        case.contributors.add(self.contributor1)
        case.save()
        
        original_id = case.id
        
        # Step 2: Attempt to create entity with invalid entity ID
        # Validation now happens at JawafEntity level
        with pytest.raises(ValidationError) as exc_info:
            from cases.models import JawafEntity
            invalid_entity = JawafEntity(nes_id="not-valid-format")
            invalid_entity.save()
        
        error_dict = exc_info.value.message_dict
        assert 'nes_id' in error_dict, \
            f"Error should be associated with nes_id field. Got: {error_dict}"
        
        # Step 4: Update with valid entity IDs
        new_entities = create_entities_from_ids(["entity:person/updated-person", "entity:organization/new-org"])
        case.alleged_entities.set(new_entities)
        case.full_clean()  # Should not raise
        case.save()
        
        # Step 5: Verify update succeeds
        case.refresh_from_db()
        
        assert case.id == original_id, \
            "Should be the same case instance"
        assert case.alleged_entities.count() == 2, \
            "Case should have 2 entity IDs after update"
        entity_nes_ids = [e.nes_id for e in case.alleged_entities.all()]
        assert "entity:person/updated-person" in entity_nes_ids, \
            "Updated entity ID should be saved"
        assert "entity:organization/new-org" in entity_nes_ids, \
            "New entity ID should be saved"
    
    def test_admin_related_entities_validation(self):
        """
        E2E Test: Verify entity ID validation for related_entities and locations fields.
        
        Workflow:
        1. Test invalid entity IDs in related_entities field
        2. Test invalid entity IDs in locations field
        3. Test valid entity IDs in all entity fields
        4. Verify all fields are properly validated
        
        Validates: Entity ID validation across all entity fields
        """
        from cases.widgets import MultiEntityIDField
        
        field = MultiEntityIDField(required=False)
        
        # Step 1: Test invalid entity IDs in related_entities field
        with pytest.raises(ValidationError) as exc_info:
            field.clean('["invalid-related"]')
        
        error_message = str(exc_info.value)
        assert 'Invalid entity ID format' in error_message, \
            f"Error should mention invalid format. Got: {error_message}"
        
        # Step 2: Test invalid entity IDs in locations field
        with pytest.raises(ValidationError) as exc_info:
            field.clean('["invalid-location"]')
        
        error_message = str(exc_info.value)
        assert 'Invalid entity ID format' in error_message, \
            f"Error should mention invalid format. Got: {error_message}"
        
        # Step 3: Test valid entity IDs in all entity fields
        result = field.clean('["entity:person/witness", "entity:organization/related-org"]')
        assert len(result) == 2, \
            "Should accept multiple valid entity IDs"
        
        result = field.clean('["entity:location/kathmandu", "entity:location/pokhara"]')
        assert len(result) == 2, \
            "Should accept multiple valid location entity IDs"
        
        # Step 4: Test empty list is valid for optional fields
        result = field.clean('[]')
        assert result == [], \
            "Empty list should be valid for optional entity fields"

    def test_alleged_entities_optional_for_draft_required_for_review(self):
        """
        E2E Test: Verify alleged_entities is optional for DRAFT but required for IN_REVIEW.
        
        Workflow:
        1. Create a draft case without alleged_entities (should succeed)
        2. Attempt to submit for review without alleged_entities (should fail)
        3. Add alleged_entities and submit (should succeed)
        4. Verify case transitions to IN_REVIEW
        
        Validates: alleged_entities validation based on state
        """
        # Step 1: Create a draft case without alleged_entities
        case = create_case_with_entities(
            title="Draft Without Entities",
            case_type=CaseType.CORRUPTION,
            alleged_entities=[],  # Empty list
            state=CaseState.DRAFT
        )
        case.contributors.add(self.contributor1)
        case.save()
        
        # Verify case was created successfully
        assert case.id is not None, \
            "Draft case should be created without alleged_entities"
        assert case.state == CaseState.DRAFT
        assert case.alleged_entities.count() == 0
        
        # Step 2: Attempt to submit for review without alleged_entities
        case.state = CaseState.IN_REVIEW
        
        with pytest.raises(ValidationError) as exc_info:
            case.validate()
        
        error_dict = exc_info.value.message_dict
        assert 'alleged_entities' in error_dict, \
            f"Should require alleged_entities for IN_REVIEW. Got errors: {error_dict}"
        error_message = str(error_dict['alleged_entities'])
        assert 'IN_REVIEW or PUBLISHED' in error_message, \
            f"Error message should mention IN_REVIEW/PUBLISHED requirement. Got: {error_message}"
        
        # Reset state
        case.state = CaseState.DRAFT
        case.save()
        
        # Step 3: Add alleged_entities and required fields for submission
        case.alleged_entities.set(create_entities_from_ids(["entity:person/corrupt-official"]))
        case.key_allegations = ["Test allegation"]
        case.description = "Test description"
        case.save()
        
        # Now submit should work
        case.submit()
        
        # Step 4: Verify case transitions to IN_REVIEW
        case.refresh_from_db()
        assert case.state == CaseState.IN_REVIEW, \
            "Case should transition to IN_REVIEW with alleged_entities"
        assert case.alleged_entities.count() == 1
        assert case.versionInfo.get('action') == 'submitted'
    
    def test_alleged_entities_required_for_published(self):
        """
        E2E Test: Verify alleged_entities is required for PUBLISHED state.
        
        Workflow:
        1. Create a draft case with alleged_entities
        2. Remove alleged_entities and attempt to publish (should fail)
        3. Add alleged_entities back and publish (should succeed)
        
        Validates: alleged_entities validation for PUBLISHED state
        """
        # Step 1: Create a draft case with alleged_entities
        case = create_case_with_entities(
            title="Case for Publishing",
            case_type=CaseType.CORRUPTION,
            alleged_entities=["entity:person/test-official"],
            key_allegations=["Test allegation"],
            description="Test description",
            state=CaseState.DRAFT
        )
        case.contributors.add(self.contributor1)
        case.save()
        
        # Step 2: Remove alleged_entities and attempt to publish
        case.alleged_entities.clear()
        case.state = CaseState.PUBLISHED
        
        with pytest.raises(ValidationError) as exc_info:
            case.validate()
        
        error_dict = exc_info.value.message_dict
        assert 'alleged_entities' in error_dict, \
            f"Should require alleged_entities for PUBLISHED. Got errors: {error_dict}"
        
        # Reset state
        case.state = CaseState.DRAFT
        case.save()
        
        # Step 3: Add alleged_entities back and publish
        case.alleged_entities.set(create_entities_from_ids(["entity:person/test-official"]))
        case.save()
        
        case.publish()
        
        case.refresh_from_db()
        assert case.state == CaseState.PUBLISHED, \
            "Case should be published with alleged_entities"
        assert case.alleged_entities.count() == 1
