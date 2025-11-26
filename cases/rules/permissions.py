import rules
from .predicates import (
    is_admin,
    is_moderator,
    is_contributor,
    is_moderator_or_admin,
    is_assigned_to_case,
    is_assigned_to_any_case,
    is_assigned_to_document_case,
    is_assigned_to_response_case,
    can_change_case_status_to_published,
    can_change_case_status_limited,
    can_view_revision,
    is_authenticated,
)

# ============================================================================
# Allegation (Case) Permissions
# ============================================================================

# View allegation - moderators/admins see all, contributors see assigned
rules.add_perm('cases.view_allegation', is_moderator_or_admin | is_assigned_to_case)

# Add allegation - all authenticated users with roles can create
rules.add_perm('cases.add_allegation', is_moderator_or_admin | is_contributor)

# Change allegation - moderators/admins or assigned contributors
rules.add_perm('cases.change_allegation', is_moderator_or_admin | is_assigned_to_case)

# Delete allegation - only moderators and admins
rules.add_perm('cases.delete_allegation', is_moderator_or_admin)

# Publish allegation - only moderators and admins
rules.add_perm('cases.publish_case', can_change_case_status_to_published)

# Assign contributors to cases - only moderators and admins
rules.add_perm('cases.assign_contributor', is_moderator_or_admin)

# Change case status - limited for contributors (draft/in_review only)
rules.add_perm('cases.change_case_status', can_change_case_status_limited)

# ============================================================================
# Document Source Permissions
# ============================================================================

# View document - moderators/admins or assigned to the case
rules.add_perm('cases.view_documentsource', is_moderator_or_admin | is_assigned_to_document_case)

# Add document - moderators/admins or contributors assigned to any case
rules.add_perm('cases.add_documentsource', is_moderator_or_admin | is_assigned_to_any_case)

# Change document - moderators/admins or assigned to the document's case
rules.add_perm('cases.change_documentsource', is_moderator_or_admin | is_assigned_to_document_case)

# Delete document - moderators/admins or assigned to the document's case
rules.add_perm('cases.delete_documentsource', is_moderator_or_admin | is_assigned_to_document_case)

# ============================================================================
# Response Permissions
# ============================================================================

# View response - moderators/admins or assigned to the case
rules.add_perm('cases.view_response', is_moderator_or_admin | is_assigned_to_response_case)

# Add response - moderators/admins or assigned contributors
rules.add_perm('cases.add_response', is_moderator_or_admin | is_assigned_to_response_case)

# Change response - moderators/admins or assigned contributors
rules.add_perm('cases.change_response', is_moderator_or_admin | is_assigned_to_response_case)

# Delete response - only moderators and admins
rules.add_perm('cases.delete_response', is_moderator_or_admin)

# Verify response - only moderators and admins
rules.add_perm('cases.verify_response', is_moderator_or_admin)

# ============================================================================
# Allegation Revision Permissions
# ============================================================================

# View revision - moderators/admins or assigned to the case
rules.add_perm('cases.view_allegationrevision', can_view_revision)

# Add revision - automatically created on save, same as change_allegation
rules.add_perm('cases.add_allegationrevision', is_moderator_or_admin | is_assigned_to_case)

# ============================================================================
# Modification (Audit Log) Permissions
# ============================================================================

# View modifications - moderators/admins or assigned to the case
rules.add_perm('cases.view_modification', is_moderator_or_admin | is_assigned_to_case)

# Add modification - automatically created, same as change_allegation
rules.add_perm('cases.add_modification', is_moderator_or_admin | is_assigned_to_case)

# ============================================================================
# User Management Permissions
# ============================================================================

# Manage moderators - only admins
rules.add_perm('cases.manage_moderators', is_admin)

# Manage contributors - moderators and admins
rules.add_perm('cases.manage_contributors', is_moderator_or_admin)

# View all users - moderators and admins
rules.add_perm('cases.view_all_users', is_moderator_or_admin)

# ============================================================================
# Django Admin Permissions
# ============================================================================

# Access to Django admin - staff users only (handled by Django)
# But we can add additional checks for specific models
rules.add_perm('cases.access_admin', is_moderator_or_admin)
