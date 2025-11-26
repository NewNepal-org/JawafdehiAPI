"""
Django REST Framework permission classes for the cases app
"""
from rest_framework import permissions


class IsModeratorOrAdmin(permissions.BasePermission):
    """
    Permission class that allows only moderators and admins
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in=['Admin', 'Moderator']).exists()


class IsAssignedContributor(permissions.BasePermission):
    """
    Permission class that checks if user is assigned to the case
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins and moderators have full access
        if request.user.groups.filter(name__in=['Admin', 'Moderator']).exists():
            return True
        
        # Check if user is assigned to the case
        # Handle different object types
        if hasattr(obj, 'contributors'):
            # Direct allegation object
            return obj.contributors.filter(id=request.user.id).exists()
        elif hasattr(obj, 'allegation'):
            # Related objects like Response, Modification
            return obj.allegation.contributors.filter(id=request.user.id).exists()
        elif hasattr(obj, 'case'):
            # DocumentSource
            if obj.case:
                return obj.case.contributors.filter(id=request.user.id).exists()
        
        return False


class AllegationPermission(permissions.BasePermission):
    """
    Custom permission for Allegation objects
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Anyone with a role can view list
        if request.method in permissions.SAFE_METHODS:
            return request.user.groups.filter(
                name__in=['Admin', 'Moderator', 'Contributor']
            ).exists()
        
        # POST (create) - all roles can create
        if request.method == 'POST':
            return request.user.groups.filter(
                name__in=['Admin', 'Moderator', 'Contributor']
            ).exists()
        
        return True
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins and moderators have full access
        if request.user.groups.filter(name__in=['Admin', 'Moderator']).exists():
            return True
        
        # Contributors can only access assigned cases
        if request.user.groups.filter(name='Contributor').exists():
            is_assigned = obj.contributors.filter(id=request.user.id).exists()
            
            # Read access for assigned cases
            if request.method in permissions.SAFE_METHODS:
                return is_assigned
            
            # Write access for assigned cases (but not delete)
            if request.method in ['PUT', 'PATCH']:
                return is_assigned
            
            # No delete access for contributors
            if request.method == 'DELETE':
                return False
        
        return False


class DocumentSourcePermission(permissions.BasePermission):
    """
    Custom permission for DocumentSource objects
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Anyone with a role can view and create documents
        return request.user.groups.filter(
            name__in=['Admin', 'Moderator', 'Contributor']
        ).exists()
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins and moderators have full access
        if request.user.groups.filter(name__in=['Admin', 'Moderator']).exists():
            return True
        
        # Contributors can access documents for their assigned cases
        if obj.case:
            return obj.case.contributors.filter(id=request.user.id).exists()
        
        # Documents without a case can be accessed by any contributor
        return request.user.groups.filter(name='Contributor').exists()


class ResponsePermission(permissions.BasePermission):
    """
    Custom permission for Response objects
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.groups.filter(
            name__in=['Admin', 'Moderator', 'Contributor']
        ).exists()
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins and moderators have full access
        if request.user.groups.filter(name__in=['Admin', 'Moderator']).exists():
            return True
        
        # Contributors can access responses for their assigned cases
        is_assigned = obj.allegation.contributors.filter(id=request.user.id).exists()
        
        # Read and write access for assigned cases
        if request.method in permissions.SAFE_METHODS or request.method in ['POST', 'PUT', 'PATCH']:
            return is_assigned
        
        # No delete access for contributors
        return False


class CanPublishCase(permissions.BasePermission):
    """
    Permission to publish cases - only moderators and admins
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in=['Admin', 'Moderator']).exists()
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in=['Admin', 'Moderator']).exists()


class CanAssignContributors(permissions.BasePermission):
    """
    Permission to assign contributors - only moderators and admins
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in=['Admin', 'Moderator']).exists()
