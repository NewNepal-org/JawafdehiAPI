import rules

# Role predicates
@rules.predicate
def is_admin(user):
    """Check if user is an Admin"""
    return user.is_authenticated and user.groups.filter(name='Admin').exists()

@rules.predicate
def is_moderator(user):
    """Check if user is a Moderator"""
    return user.is_authenticated and user.groups.filter(name='Moderator').exists()

@rules.predicate
def is_contributor(user):
    """Check if user is a Contributor"""
    return user.is_authenticated and user.groups.filter(name='Contributor').exists()

@rules.predicate
def is_moderator_or_admin(user):
    """Check if user is either a Moderator or Admin"""
    return is_admin(user) or is_moderator(user)

@rules.predicate
def is_authenticated(user):
    """Check if user is authenticated"""
    return user.is_authenticated

# Case/Allegation predicates
@rules.predicate
def is_assigned_to_case(user, allegation):
    """Check if user is assigned as a contributor to this case"""
    if not user.is_authenticated:
        return False
    return allegation.contributors.filter(id=user.id).exists()

@rules.predicate
def is_assigned_to_any_case(user):
    """Check if user is assigned to at least one case"""
    if not user.is_authenticated:
        return False
    from cases.models import Allegation
    return Allegation.objects.filter(contributors=user).exists()

@rules.predicate
def can_change_case_status_to_published(user, allegation):
    """Only moderators and admins can publish cases"""
    return is_moderator_or_admin(user)

@rules.predicate
def can_change_case_status_limited(user, allegation):
    """Contributors can only change status between Draft and In Review"""
    if not user.is_authenticated:
        return False
    if is_moderator_or_admin(user):
        return True
    if is_assigned_to_case(user, allegation):
        # Contributors can only toggle between draft and in_review
        return allegation.state in ['draft', 'in_review']
    return False

# Document predicates
@rules.predicate
def is_assigned_to_document_case(user, document):
    """Check if user is assigned to the case this document belongs to"""
    if not user.is_authenticated or not document.case:
        return False
    return document.case.contributors.filter(id=user.id).exists()

# Response predicates
@rules.predicate
def is_assigned_to_response_case(user, response):
    """Check if user is assigned to the case this response belongs to"""
    if not user.is_authenticated:
        return False
    return response.allegation.contributors.filter(id=user.id).exists()

# Revision predicates
@rules.predicate
def can_view_revision(user, revision):
    """Check if user can view this revision"""
    if not user.is_authenticated:
        return False
    if is_moderator_or_admin(user):
        return True
    return revision.allegation.contributors.filter(id=user.id).exists()
