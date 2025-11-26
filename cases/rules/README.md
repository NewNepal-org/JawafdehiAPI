# Permission System Documentation

This directory contains the permission system for the Nepal Public Accountability Portal using `django-rules`.

## Overview

The permission system implements role-based access control (RBAC) with three main roles:
- **Admin**: Full system access, can manage moderators and contributors
- **Moderator**: Can manage contributors and all cases
- **Contributor**: Can only access assigned cases

## Files

### `predicates.py`
Contains rule predicates that define the conditions for permissions. These are reusable building blocks for permission rules.

Key predicates:
- `is_admin(user)` - Check if user is an Admin
- `is_moderator(user)` - Check if user is a Moderator
- `is_contributor(user)` - Check if user is a Contributor
- `is_assigned_to_case(user, allegation)` - Check if user is assigned to a case
- `can_change_case_status_limited(user, allegation)` - Contributors can only change between Draft/In Review

### `permissions.py`
Defines the actual permission rules by combining predicates. These are registered with django-rules and can be checked using Django's standard permission system.

Permission format: `app_label.permission_name`

Examples:
- `cases.view_allegation` - View an allegation
- `cases.change_allegation` - Edit an allegation
- `cases.publish_case` - Publish a case (moderators/admins only)
- `cases.assign_contributor` - Assign contributors to cases

### `utils.py`
Helper functions for checking permissions in views and APIs.

Key functions:
- `check_object_permission(user, perm, obj)` - Check permission or raise PermissionDenied
- `user_can_view_case(user, allegation)` - Check if user can view a case
- `get_user_accessible_cases(user)` - Get all cases user can access
- `filter_cases_by_permission(user, queryset)` - Filter queryset by permissions

## Usage

### In Django Views

```python
from django.contrib.auth.decorators import login_required
from rules.contrib.views import permission_required
from cases.rules import check_object_permission, user_can_view_case

@login_required
@permission_required('cases.view_allegation', fn=lambda request, pk: Allegation.objects.get(pk=pk))
def view_case(request, pk):
    allegation = get_object_or_404(Allegation, pk=pk)
    # View logic here
    return render(request, 'case_detail.html', {'allegation': allegation})
```

### In Django REST Framework

```python
from rest_framework import viewsets
from cases.permissions import AllegationPermission

class AllegationViewSet(viewsets.ModelViewSet):
    queryset = Allegation.objects.all()
    serializer_class = AllegationSerializer
    permission_classes = [AllegationPermission]
    
    def get_queryset(self):
        # Filter by user permissions
        from cases.rules import filter_cases_by_permission
        return filter_cases_by_permission(self.request.user, self.queryset)
```

### Checking Permissions Programmatically

```python
# Check if user has permission
if request.user.has_perm('cases.view_allegation', allegation):
    # User can view this allegation
    pass

# Using helper functions
from cases.rules import user_can_edit_case, user_can_publish_case

if user_can_edit_case(request.user, allegation):
    # User can edit
    pass

if user_can_publish_case(request.user, allegation):
    # User can publish
    pass
```

### In Templates

```django
{% load rules %}

{% has_perm 'cases.change_allegation' user allegation as can_edit %}
{% if can_edit %}
    <a href="{% url 'edit_case' allegation.pk %}">Edit Case</a>
{% endif %}

{% has_perm 'cases.publish_case' user allegation as can_publish %}
{% if can_publish %}
    <button>Publish Case</button>
{% endif %}
```

## Setup

1. Install dependencies:
```bash
poetry install
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Create user groups:
```bash
python manage.py setup_groups
```

4. Assign users to groups in Django admin or programmatically:
```python
from django.contrib.auth.models import User, Group

user = User.objects.get(username='john')
contributor_group = Group.objects.get(name='Contributor')
user.groups.add(contributor_group)
```

## Permission Matrix

| Action | Admin | Moderator | Contributor |
|--------|-------|-----------|-------------|
| View all cases | ✓ | ✓ | ✗ |
| View assigned cases | ✓ | ✓ | ✓ |
| Create cases | ✓ | ✓ | ✓ |
| Edit assigned cases | ✓ | ✓ | ✓ |
| Delete cases | ✓ | ✓ | ✗ |
| Publish cases | ✓ | ✓ | ✗ |
| Assign contributors | ✓ | ✓ | ✗ |
| Manage moderators | ✓ | ✗ | ✗ |
| Manage contributors | ✓ | ✓ | ✗ |
| Change status (all) | ✓ | ✓ | ✗ |
| Change status (Draft↔In Review) | ✓ | ✓ | ✓ |

## Testing Permissions

```python
from django.test import TestCase
from django.contrib.auth.models import User, Group
from cases.models import Allegation

class PermissionTestCase(TestCase):
    def setUp(self):
        # Create groups
        self.admin_group = Group.objects.create(name='Admin')
        self.contributor_group = Group.objects.create(name='Contributor')
        
        # Create users
        self.admin = User.objects.create_user('admin', 'admin@test.com', 'pass')
        self.admin.groups.add(self.admin_group)
        
        self.contributor = User.objects.create_user('contributor', 'contrib@test.com', 'pass')
        self.contributor.groups.add(self.contributor_group)
        
        # Create case
        self.case = Allegation.objects.create(
            title='Test Case',
            allegation_type='corruption',
            description='Test'
        )
    
    def test_admin_can_view_all_cases(self):
        self.assertTrue(self.admin.has_perm('cases.view_allegation', self.case))
    
    def test_contributor_cannot_view_unassigned_case(self):
        self.assertFalse(self.contributor.has_perm('cases.view_allegation', self.case))
    
    def test_contributor_can_view_assigned_case(self):
        self.case.contributors.add(self.contributor)
        self.assertTrue(self.contributor.has_perm('cases.view_allegation', self.case))
```

## Troubleshooting

### Permissions not working
1. Ensure `rules.apps.AutodiscoverRulesConfig` is in `INSTALLED_APPS`
2. Ensure `rules.permissions.ObjectPermissionBackend` is in `AUTHENTICATION_BACKENDS`
3. Check that groups are created: `python manage.py setup_groups`
4. Verify user is in correct group: `user.groups.all()`

### Object permissions not checking
Make sure you're passing the object when checking permissions:
```python
# Wrong
user.has_perm('cases.view_allegation')

# Correct
user.has_perm('cases.view_allegation', allegation)
```
