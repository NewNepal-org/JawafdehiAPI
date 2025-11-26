"""
Utility functions for permission checking in views and APIs
"""
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from rules.contrib.views import permission_required


def check_object_permission(user, perm, obj):
    """
    Check if user has permission for a specific object.
    Raises PermissionDenied if not.
    
    Args:
        user: Django User instance
        perm: Permission string (e.g., 'cases.change_allegation')
        obj: Object to check permission against
        
    Raises:
        PermissionDenied: If user doesn't have permission
    """
    if not user.has_perm(perm, obj):
        raise PermissionDenied(f"You do not have permission to perform this action.")


def user_can_view_case(user, allegation):
    """Check if user can view a specific allegation"""
    return user.has_perm('cases.view_allegation', allegation)


def user_can_edit_case(user, allegation):
    """Check if user can edit a specific allegation"""
    return user.has_perm('cases.change_allegation', allegation)


def user_can_publish_case(user, allegation):
    """Check if user can publish a specific allegation"""
    return user.has_perm('cases.publish_case', allegation)


def user_can_assign_contributors(user):
    """Check if user can assign contributors to cases"""
    return user.has_perm('cases.assign_contributor')


def user_can_manage_moderators(user):
    """Check if user can manage moderators"""
    return user.has_perm('cases.manage_moderators')


def user_can_manage_contributors(user):
    """Check if user can manage contributors"""
    return user.has_perm('cases.manage_contributors')


def get_user_accessible_cases(user):
    """
    Get all cases that a user has access to view.
    
    Args:
        user: Django User instance
        
    Returns:
        QuerySet of Allegation objects
    """
    from cases.models import Allegation
    
    if not user.is_authenticated:
        return Allegation.objects.none()
    
    # Admins and moderators see all cases
    if user.groups.filter(name__in=['Admin', 'Moderator']).exists():
        return Allegation.objects.all()
    
    # Contributors see only assigned cases
    return Allegation.objects.filter(contributors=user)


def filter_cases_by_permission(user, queryset):
    """
    Filter a queryset of cases based on user permissions.
    
    Args:
        user: Django User instance
        queryset: QuerySet of Allegation objects
        
    Returns:
        Filtered QuerySet
    """
    if not user.is_authenticated:
        return queryset.none()
    
    # Admins and moderators see all
    if user.groups.filter(name__in=['Admin', 'Moderator']).exists():
        return queryset
    
    # Contributors see only assigned cases
    return queryset.filter(contributors=user)
