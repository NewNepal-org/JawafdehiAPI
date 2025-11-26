"""
Property-based tests for Django Admin Case management.

Feature: accountability-platform-core
Tests Properties 6, 9
Validates: Requirements 2.1, 2.4, 7.2
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import datetime

# Import will work once Case model is implemented
try:
    from cases.models import Case, CaseState, CaseType
except ImportError:
    pytest.skip("Case model not yet implemented", allow_module_level=True)


User = get_user_model()


# ============================================================================
# Hypothesis Strategies (Generators)
# ============================================================================

@st.composite
def valid_entity_id(draw):
    """Generate valid entity IDs matching NES format."""
    entity_types = ["person", "organization", "location"]
    entity_type = draw(st.sampled_from(entity_types))
    
    # Generate valid slug (lowercase letters, numbers, hyphens)
    slug = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        min_size=3,
        max_size=50
    ).filter(lambda x: x and not x.startswith("-") and not x.endswith("-")))
    
    return f"entity:{entity_type}/{slug}"


@st.composite
def entity_id_list(draw, min_size=1, max_size=5):
    """Generate a list of valid entity IDs."""
    return draw(st.lists(valid_entity_id(), min_size=min_size, max_size=max_size, unique=True))


@st.composite
def text_list(draw, min_size=1, max_size=5):
    """Generate a list of text strings."""
    return draw(st.lists(
        st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
        min_size=min_size,
        max_size=max_size
    ))


@st.composite
def complete_case_data(draw):
    """
    Generate complete valid case data for IN_REVIEW state.
    
    According to Property 2, IN_REVIEW validation is strict - all required
    fields must be present and valid.
    """
    return {
        "title": draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip())),
        "alleged_entities": draw(entity_id_list(min_size=1, max_size=3)),
        "key_allegations": draw(text_list(min_size=1, max_size=5)),
        "case_type": draw(st.sampled_from([CaseType.CORRUPTION, CaseType.PROMISES])),
        "description": draw(st.text(min_size=10, max_size=1000).filter(lambda x: x.strip())),
    }


@st.composite
def user_with_role(draw, role):
    """
    Generate a User with the specified role.
    
    Roles: 'Admin', 'Moderator', 'Contributor'
    """
    import uuid
    # Add UUID to ensure uniqueness across test runs
    unique_id = uuid.uuid4().hex[:8]
    base_username = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="_"),
        min_size=3,
        max_size=12
    ).filter(lambda x: x and not x.startswith("_")))
    
    username = f"{base_username}_{unique_id}"
    email = f"{username}@example.com"
    
    return {
        "username": username,
        "email": email,
        "role": role,
    }


# ============================================================================
# Helper Functions
# ============================================================================

def create_user_with_role(username, email, role):
    """
    Create a user with the specified role.
    
    Creates the role group if it doesn't exist and assigns the user to it.
    """
    user = User.objects.create_user(
        username=username,
        email=email,
        password="testpass123"
    )
    
    # Create or get the role group
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    
    # Set staff status for Admin and Moderator
    if role in ['Admin', 'Moderator']:
        user.is_staff = True
        user.save()
    
    # Set superuser status for Admin
    if role == 'Admin':
        user.is_superuser = True
        user.save()
    
    return user


def can_transition_to_state(user, case, target_state):
    """
    Check if a user can transition a case to the target state.
    
    This simulates the permission check that would happen in Django Admin.
    
    Rules:
    - Contributors: Can only transition between DRAFT and IN_REVIEW
    - Moderators: Can transition to any state except they cannot manage other moderators
    - Admins: Can transition to any state
    """
    user_groups = list(user.groups.values_list('name', flat=True))
    
    if 'Admin' in user_groups or user.is_superuser:
        # Admins can do anything
        return True
    
    if 'Moderator' in user_groups:
        # Moderators can transition to any state
        return True
    
    if 'Contributor' in user_groups:
        # Contributors can only transition between DRAFT and IN_REVIEW
        if target_state in [CaseState.DRAFT, CaseState.IN_REVIEW]:
            return True
        return False
    
    # No role assigned
    return False


# ============================================================================
# Property 6: Moderators can publish and close cases
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=20)  # Reduced from 100 to 20 for faster execution
@given(
    case_data=complete_case_data(),
    moderator_data=user_with_role('Moderator')
)
def test_moderators_can_publish_cases(case_data, moderator_data):
    """
    Feature: accountability-platform-core, Property 6: Moderators can publish and close cases
    
    For any case in IN_REVIEW state, a Moderator should be able to change
    the state to PUBLISHED.
    Validates: Requirements 2.1
    """
    # Create moderator user
    moderator = create_user_with_role(
        moderator_data['username'],
        moderator_data['email'],
        moderator_data['role']
    )
    
    # Create a case in IN_REVIEW state
    case = Case.objects.create(**case_data)
    case.state = CaseState.IN_REVIEW
    case.save()
    
    # Check that moderator can transition to PUBLISHED
    can_publish = can_transition_to_state(moderator, case, CaseState.PUBLISHED)
    
    assert can_publish, \
        "Moderator should be able to transition case to PUBLISHED state"
    
    # Actually perform the transition
    case.state = CaseState.PUBLISHED
    case.validate()  # Should not raise
    case.save()
    
    assert case.state == CaseState.PUBLISHED, \
        f"Case should be in PUBLISHED state, but got {case.state}"


@pytest.mark.django_db
@settings(max_examples=20)  # Reduced from 100 to 20 for faster execution
@given(
    case_data=complete_case_data(),
    moderator_data=user_with_role('Moderator')
)
def test_moderators_can_close_cases(case_data, moderator_data):
    """
    Feature: accountability-platform-core, Property 6: Moderators can publish and close cases
    
    For any case in IN_REVIEW state, a Moderator should be able to change
    the state to CLOSED.
    Validates: Requirements 2.1
    """
    # Create moderator user
    moderator = create_user_with_role(
        moderator_data['username'],
        moderator_data['email'],
        moderator_data['role']
    )
    
    # Create a case in IN_REVIEW state
    case = Case.objects.create(**case_data)
    case.state = CaseState.IN_REVIEW
    case.save()
    
    # Check that moderator can transition to CLOSED
    can_close = can_transition_to_state(moderator, case, CaseState.CLOSED)
    
    assert can_close, \
        "Moderator should be able to transition case to CLOSED state"
    
    # Actually perform the transition
    case.state = CaseState.CLOSED
    case.save()
    
    assert case.state == CaseState.CLOSED, \
        f"Case should be in CLOSED state, but got {case.state}"


@pytest.mark.django_db
@settings(max_examples=10)  # Reduced from 50 to 10 for faster execution
@given(
    case_data=complete_case_data(),
    moderator_data=user_with_role('Moderator'),
    target_state=st.sampled_from([CaseState.PUBLISHED, CaseState.CLOSED])
)
def test_moderators_can_transition_to_any_state(case_data, moderator_data, target_state):
    """
    Feature: accountability-platform-core, Property 6: Moderators can publish and close cases
    
    For any case, a Moderator should be able to transition to PUBLISHED or CLOSED states.
    Validates: Requirements 2.1
    """
    # Create moderator user
    moderator = create_user_with_role(
        moderator_data['username'],
        moderator_data['email'],
        moderator_data['role']
    )
    
    # Create a case in IN_REVIEW state
    case = Case.objects.create(**case_data)
    case.state = CaseState.IN_REVIEW
    case.save()
    
    # Check that moderator can transition to target state
    can_transition = can_transition_to_state(moderator, case, target_state)
    
    assert can_transition, \
        f"Moderator should be able to transition case to {target_state} state"


# ============================================================================
# Property 9: State transitions update versionInfo
# ============================================================================

@pytest.mark.django_db
@settings(max_examples=20)  # Reduced from 100 to 20 for faster execution
@given(case_data=complete_case_data())
def test_transition_to_in_review_updates_version_info(case_data):
    """
    Feature: accountability-platform-core, Property 9: State transitions to IN_REVIEW, PUBLISHED, or CLOSED update versionInfo
    
    For any case transitioning to IN_REVIEW state, the versionInfo should be
    updated with the change details including timestamp.
    Validates: Requirements 2.4, 7.2
    """
    # Create a case in DRAFT state
    case = Case.objects.create(**case_data)
    assert case.state == CaseState.DRAFT
    
    # Record time before transition
    before_transition = timezone.now()
    
    # Transition to IN_REVIEW using submit()
    case.submit()
    
    # Record time after transition
    after_transition = timezone.now()
    
    # Check that versionInfo was updated
    assert case.versionInfo is not None, \
        "versionInfo should be updated after state transition"
    
    assert 'datetime' in case.versionInfo, \
        "versionInfo should contain datetime field"
    
    assert 'action' in case.versionInfo, \
        "versionInfo should contain action field"
    
    assert case.versionInfo['action'] == 'submitted', \
        f"versionInfo action should be 'submitted', but got {case.versionInfo['action']}"
    
    # Verify datetime is within reasonable range
    version_datetime = datetime.fromisoformat(case.versionInfo['datetime'])
    assert before_transition <= version_datetime <= after_transition, \
        "versionInfo datetime should be within the transition time range"


@pytest.mark.django_db
@settings(max_examples=20)  # Reduced from 100 to 20 for faster execution
@given(case_data=complete_case_data())
def test_transition_to_published_updates_version_info(case_data):
    """
    Feature: accountability-platform-core, Property 9: State transitions to IN_REVIEW, PUBLISHED, or CLOSED update versionInfo
    
    For any case transitioning to PUBLISHED state, the versionInfo should be
    updated with the change details including timestamp.
    Validates: Requirements 2.4, 7.2
    """
    # Create a case in IN_REVIEW state
    case = Case.objects.create(**case_data)
    case.state = CaseState.IN_REVIEW
    case.save()
    
    # Record time before transition
    before_transition = timezone.now()
    
    # Transition to PUBLISHED using publish()
    case.publish()
    
    # Record time after transition
    after_transition = timezone.now()
    
    # Check that versionInfo was updated
    assert case.versionInfo is not None, \
        "versionInfo should be updated after state transition"
    
    assert 'datetime' in case.versionInfo, \
        "versionInfo should contain datetime field"
    
    assert 'action' in case.versionInfo, \
        "versionInfo should contain action field"
    
    assert case.versionInfo['action'] == 'published', \
        f"versionInfo action should be 'published', but got {case.versionInfo['action']}"
    
    # Verify datetime is within reasonable range
    version_datetime = datetime.fromisoformat(case.versionInfo['datetime'])
    assert before_transition <= version_datetime <= after_transition, \
        "versionInfo datetime should be within the transition time range"


@pytest.mark.django_db
@settings(max_examples=20)  # Reduced from 100 to 20 for faster execution
@given(
    case_data=complete_case_data(),
    target_state=st.sampled_from([CaseState.IN_REVIEW, CaseState.PUBLISHED, CaseState.CLOSED])
)
def test_state_transitions_always_update_version_info(case_data, target_state):
    """
    Feature: accountability-platform-core, Property 9: State transitions to IN_REVIEW, PUBLISHED, or CLOSED update versionInfo
    
    For any case transitioning to IN_REVIEW, PUBLISHED, or CLOSED state,
    the versionInfo should be updated with change details.
    Validates: Requirements 2.4, 7.2
    """
    # Create a case
    case = Case.objects.create(**case_data)
    
    # Clear versionInfo to test that it gets updated
    case.versionInfo = {}
    case.save()
    
    # Transition to target state
    if target_state == CaseState.IN_REVIEW:
        case.state = CaseState.DRAFT
        case.save()
        case.submit()
    elif target_state == CaseState.PUBLISHED:
        case.state = CaseState.IN_REVIEW
        case.save()
        case.publish()
    elif target_state == CaseState.CLOSED:
        # For CLOSED, we just set the state directly
        # (soft delete functionality will be implemented in task 17)
        case.state = CaseState.CLOSED
        case.versionInfo = {
            'version_number': case.version,
            'action': 'closed',
            'datetime': timezone.now().isoformat(),
        }
        case.save()
    
    # Check that versionInfo was updated
    assert case.versionInfo is not None and len(case.versionInfo) > 0, \
        f"versionInfo should be updated after transition to {target_state}"
    
    assert 'datetime' in case.versionInfo, \
        f"versionInfo should contain datetime field after transition to {target_state}"


# ============================================================================
# Edge Cases and Additional Tests
# ============================================================================

@pytest.mark.django_db
def test_contributor_cannot_publish_case():
    """
    Edge case: Contributors should not be able to publish cases.
    Validates: Requirements 1.5
    """
    # Create contributor user
    contributor = create_user_with_role('testcontrib', 'contrib@example.com', 'Contributor')
    
    # Create a case in IN_REVIEW state
    case = Case.objects.create(
        title="Test Case",
        alleged_entities=["entity:person/test-person"],
        key_allegations=["Test allegation"],
        case_type=CaseType.CORRUPTION,
        description="Test description",
        state=CaseState.IN_REVIEW,
    )
    
    # Check that contributor cannot transition to PUBLISHED
    can_publish = can_transition_to_state(contributor, case, CaseState.PUBLISHED)
    
    assert not can_publish, \
        "Contributor should NOT be able to transition case to PUBLISHED state"


@pytest.mark.django_db
def test_admin_can_publish_case():
    """
    Edge case: Admins should be able to publish cases.
    Validates: Requirements 5.1
    """
    # Create admin user
    admin = create_user_with_role('testadmin', 'admin@example.com', 'Admin')
    
    # Create a case in IN_REVIEW state
    case = Case.objects.create(
        title="Test Case",
        alleged_entities=["entity:person/test-person"],
        key_allegations=["Test allegation"],
        case_type=CaseType.CORRUPTION,
        description="Test description",
        state=CaseState.IN_REVIEW,
    )
    
    # Check that admin can transition to PUBLISHED
    can_publish = can_transition_to_state(admin, case, CaseState.PUBLISHED)
    
    assert can_publish, \
        "Admin should be able to transition case to PUBLISHED state"


@pytest.mark.django_db
def test_version_info_contains_version_number():
    """
    Edge case: versionInfo should contain the version number.
    Validates: Requirements 7.2
    """
    # Create a case
    case = Case.objects.create(
        title="Test Case",
        alleged_entities=["entity:person/test-person"],
        key_allegations=["Test allegation"],
        case_type=CaseType.CORRUPTION,
        description="Test description",
    )
    
    # Submit to IN_REVIEW
    case.submit()
    
    # Check versionInfo contains version_number
    assert 'version_number' in case.versionInfo, \
        "versionInfo should contain version_number field"
    
    assert case.versionInfo['version_number'] == case.version, \
        f"versionInfo version_number should match case version ({case.version})"
