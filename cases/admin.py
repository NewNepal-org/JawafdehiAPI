from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django import forms
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from tinymce.widgets import TinyMCE
from .models import Case, DocumentSource, CaseState, CaseType
from .widgets import (
    MultiEntityIDField,
    MultiTextField,
    MultiTimelineField,
    MultiEvidenceField,
)

User = get_user_model()


# ============================================================================
# Custom Admin Forms
# ============================================================================

class CaseAdminForm(forms.ModelForm):
    """
    Custom form for Case admin with rich text editor and custom widgets.
    """
    
    # Override fields with custom widgets
    alleged_entities = MultiEntityIDField(
        required=True,
        label="Alleged Entities",
        help_text="Entity IDs for entities being accused"
    )
    
    related_entities = MultiEntityIDField(
        required=False,
        label="Related Entities",
        help_text="Entity IDs for related entities"
    )
    
    locations = MultiEntityIDField(
        required=False,
        label="Locations",
        help_text="Location entity IDs"
    )
    
    key_allegations = MultiTextField(
        required=False,
        label="Key Allegations",
        help_text="List of key allegation statements"
    )
    
    tags = MultiTextField(
        required=False,
        label="Tags",
        help_text="Tags for categorization"
    )
    
    timeline = MultiTimelineField(
        required=False,
        label="Timeline",
        help_text="Timeline of events"
    )
    
    evidence = MultiEvidenceField(
        required=False,
        label="Evidence",
        help_text="Evidence entries with source references"
    )
    
    class Meta:
        model = Case
        fields = '__all__'
        widgets = {
            'description': TinyMCE(attrs={'cols': 80, 'rows': 30}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate evidence field with available sources
        sources = DocumentSource.objects.filter(is_deleted=False).values_list('source_id', 'title')
        self.fields['evidence'].sources = list(sources)
        self.fields['evidence'].widget.sources = list(sources)
    
    def clean(self):
        """
        Validate the form based on the current state.
        """
        cleaned_data = super().clean()
        state = cleaned_data.get('state')
        
        # Validate based on state
        if state in [CaseState.IN_REVIEW, CaseState.PUBLISHED]:
            # Strict validation for IN_REVIEW and PUBLISHED
            if not cleaned_data.get('key_allegations'):
                raise ValidationError({
                    'key_allegations': 'At least one key allegation is required for IN_REVIEW or PUBLISHED state'
                })
            
            if not cleaned_data.get('description') or not cleaned_data.get('description').strip():
                raise ValidationError({
                    'description': 'Description is required for IN_REVIEW or PUBLISHED state'
                })
        
        return cleaned_data


# ============================================================================
# Case Admin
# ============================================================================

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """
    Django Admin configuration for Case model.
    
    Features:
    - Custom form with rich text editor
    - State transition controls with validation
    - Version history display
    - Contributor assignment
    - Role-based permissions
    """
    
    form = CaseAdminForm
    
    list_display = [
        'case_id',
        'version',
        'title',
        'case_type',
        'state_badge',
        'created_at',
        'updated_at',
    ]
    
    list_filter = [
        'state',
        'case_type',
        'created_at',
    ]
    
    search_fields = [
        'case_id',
        'title',
        'description',
    ]
    
    readonly_fields = [
        'case_id',
        'version',
        'created_at',
        'updated_at',
        'version_info_display',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'case_id',
                'version',
                'title',
                'case_type',
                'state',
            )
        }),
        ('Dates', {
            'fields': (
                'case_start_date',
                'case_end_date',
            )
        }),
        ('Entities', {
            'fields': (
                'alleged_entities',
                'related_entities',
                'locations',
            )
        }),
        ('Content', {
            'fields': (
                'description',
                'key_allegations',
                'tags',
            )
        }),
        ('Timeline & Evidence', {
            'fields': (
                'timeline',
                'evidence',
            )
        }),
        ('Assignment', {
            'fields': (
                'contributors',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
                'version_info_display',
            ),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ['contributors']
    
    def state_badge(self, obj):
        """Display state as a colored badge."""
        colors = {
            CaseState.DRAFT: '#6c757d',
            CaseState.IN_REVIEW: '#ffc107',
            CaseState.PUBLISHED: '#28a745',
            CaseState.CLOSED: '#dc3545',
        }
        color = colors.get(obj.state, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_state_display()
        )
    state_badge.short_description = 'State'
    
    def version_info_display(self, obj):
        """Display version info in a readable format."""
        if not obj.versionInfo:
            return "No version info"
        
        info = obj.versionInfo
        html = "<div style='font-family: monospace;'>"
        
        if 'version_number' in info:
            html += f"<strong>Version:</strong> {info['version_number']}<br>"
        
        if 'action' in info:
            html += f"<strong>Action:</strong> {info['action']}<br>"
        
        if 'datetime' in info:
            html += f"<strong>DateTime:</strong> {info['datetime']}<br>"
        
        if 'source_version' in info:
            html += f"<strong>Source Version:</strong> {info['source_version']}<br>"
        
        if 'user_id' in info:
            html += f"<strong>User ID:</strong> {info['user_id']}<br>"
        
        if 'change_summary' in info:
            html += f"<strong>Summary:</strong> {info['change_summary']}<br>"
        
        html += "</div>"
        return format_html(html)
    version_info_display.short_description = 'Version Info'
    
    def get_queryset(self, request):
        """
        Filter queryset based on user role.
        
        - Contributors: Only see assigned cases
        - Moderators/Admins: See all cases
        """
        qs = super().get_queryset(request)
        
        # Admins and superusers see everything
        if request.user.is_superuser:
            return qs
        
        # Check user groups
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Moderators see everything
        if 'Moderator' in user_groups or 'Admin' in user_groups:
            return qs
        
        # Contributors only see assigned cases
        if 'Contributor' in user_groups:
            return qs.filter(contributors=request.user)
        
        # No role - see nothing
        return qs.none()
    
    def has_change_permission(self, request, obj=None):
        """
        Check if user can change a case.
        
        - Contributors: Can only change assigned cases
        - Moderators/Admins: Can change all cases
        """
        if not super().has_change_permission(request, obj):
            return False
        
        if obj is None:
            return True
        
        # Admins and superusers can change everything
        if request.user.is_superuser:
            return True
        
        # Check user groups
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Moderators and Admins can change everything
        if 'Moderator' in user_groups or 'Admin' in user_groups:
            return True
        
        # Contributors can only change assigned cases
        if 'Contributor' in user_groups:
            return obj.contributors.filter(id=request.user.id).exists()
        
        return False
    
    def save_model(self, request, obj, form, change):
        """
        Save the model with validation and state transition checks.
        """
        # Check if state is being changed
        if change:
            old_obj = Case.objects.get(pk=obj.pk)
            old_state = old_obj.state
            new_state = obj.state
            
            # Check if user can transition to new state
            if old_state != new_state:
                user_groups = list(request.user.groups.values_list('name', flat=True))
                
                # Contributors can only transition between DRAFT and IN_REVIEW
                if 'Contributor' in user_groups and 'Moderator' not in user_groups and 'Admin' not in user_groups:
                    if new_state not in [CaseState.DRAFT, CaseState.IN_REVIEW]:
                        raise ValidationError(
                            f"Contributors can only transition between DRAFT and IN_REVIEW states. "
                            f"Cannot transition to {new_state}."
                        )
        
        # Validate before saving
        try:
            obj.validate()
        except ValidationError as e:
            # Re-raise with form context
            raise ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        
        super().save_model(request, obj, form, change)
    
    def get_actions(self, request):
        """
        Get available actions based on user role.
        """
        actions = super().get_actions(request)
        
        # Add custom actions for state transitions
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        if 'Moderator' in user_groups or 'Admin' in user_groups or request.user.is_superuser:
            # Moderators and Admins can publish and close
            actions['publish_cases'] = (
                self.publish_cases,
                'publish_cases',
                'Publish selected cases'
            )
            actions['close_cases'] = (
                self.close_cases,
                'close_cases',
                'Close selected cases'
            )
        
        return actions
    
    def publish_cases(self, request, queryset):
        """
        Bulk action to publish cases.
        """
        count = 0
        for case in queryset:
            try:
                if case.state in [CaseState.IN_REVIEW, CaseState.DRAFT]:
                    case.publish()
                    count += 1
            except ValidationError:
                pass
        
        self.message_user(request, f"{count} case(s) published successfully.")
    publish_cases.short_description = "Publish selected cases"
    
    def close_cases(self, request, queryset):
        """
        Bulk action to close cases.
        """
        count = queryset.update(state=CaseState.CLOSED)
        self.message_user(request, f"{count} case(s) closed successfully.")
    close_cases.short_description = "Close selected cases"


# ============================================================================
# DocumentSource Admin
# ============================================================================

class DocumentSourceAdminForm(forms.ModelForm):
    """
    Custom form for DocumentSource admin with custom widgets.
    """
    
    # Override related_entity_ids with custom widget
    related_entity_ids = MultiEntityIDField(
        required=False,
        label="Related Entity IDs",
        help_text="Entity IDs related to this source"
    )
    
    # Override url field to set assume_scheme and silence Django 6.0 warning
    url = forms.URLField(
        required=False,
        max_length=500,
        assume_scheme='https',
        help_text="Optional URL to the source"
    )
    
    class Meta:
        model = DocumentSource
        fields = '__all__'
    
    def clean(self):
        """
        Validate the form.
        """
        cleaned_data = super().clean()
        
        # Validate title is not empty
        title = cleaned_data.get('title')
        if not title or not title.strip():
            raise ValidationError({
                'title': 'Title is required and cannot be empty'
            })
        
        # Validate description is not empty
        description = cleaned_data.get('description')
        if not description or not description.strip():
            raise ValidationError({
                'description': 'Description is required and cannot be empty'
            })
        
        return cleaned_data


@admin.register(DocumentSource)
class DocumentSourceAdmin(admin.ModelAdmin):
    """
    Django Admin configuration for DocumentSource model.
    
    Features:
    - Custom form with entity ID validation
    - Soft deletion interface
    - Role-based permissions
    """
    
    form = DocumentSourceAdminForm
    
    list_display = [
        'source_id',
        'title',
        'case',
        'deletion_status',
        'created_at',
    ]
    
    list_filter = [
        'is_deleted',
        'created_at',
    ]
    
    search_fields = [
        'source_id',
        'title',
        'description',
    ]
    
    readonly_fields = [
        'source_id',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'source_id',
                'title',
                'description',
                'url',
            )
        }),
        ('Relationships', {
            'fields': (
                'case',
                'related_entity_ids',
            )
        }),
        ('Status', {
            'fields': (
                'is_deleted',
            ),
            'description': 'Soft deletion: marking as deleted preserves the source in the database for audit purposes'
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def deletion_status(self, obj):
        """Display deletion status as a colored badge."""
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
                'Deleted'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            'Active'
        )
    deletion_status.short_description = 'Status'
    
    def get_queryset(self, request):
        """
        Filter queryset based on user role.
        
        - Contributors: Only see sources for assigned cases
        - Moderators/Admins: See all sources
        """
        qs = super().get_queryset(request)
        
        # Admins and superusers see everything
        if request.user.is_superuser:
            return qs
        
        # Check user groups
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Moderators see everything
        if 'Moderator' in user_groups or 'Admin' in user_groups:
            return qs
        
        # Contributors only see sources for assigned cases
        if 'Contributor' in user_groups:
            return qs.filter(case__contributors=request.user)
        
        # No role - see nothing
        return qs.none()
    
    def has_change_permission(self, request, obj=None):
        """
        Check if user can change a source.
        
        - Contributors: Can only change sources for assigned cases
        - Moderators/Admins: Can change all sources
        """
        # Check if user has staff status
        if not request.user.is_staff:
            return False
        
        if obj is None:
            return True
        
        # Admins and superusers can change everything
        if request.user.is_superuser:
            return True
        
        # Check user groups
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Moderators and Admins can change everything
        if 'Moderator' in user_groups or 'Admin' in user_groups:
            return True
        
        # Contributors can only change sources for assigned cases
        if 'Contributor' in user_groups:
            if obj.case:
                return obj.case.contributors.filter(id=request.user.id).exists()
            # Sources without a case can be edited by any contributor
            return True
        
        return False
    
    def has_delete_permission(self, request, obj=None):
        """
        Prevent hard deletion - use soft deletion instead.
        
        Hard deletion is disabled to preserve audit history.
        Users should set is_deleted=True instead.
        """
        # Disable hard deletion for all users
        return False
    
    def save_model(self, request, obj, form, change):
        """
        Save the model with validation.
        """
        # Validate before saving
        try:
            obj.validate()
        except ValidationError as e:
            # Re-raise with form context
            raise ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        
        super().save_model(request, obj, form, change)
    
    def get_actions(self, request):
        """
        Get available actions based on user role.
        """
        actions = super().get_actions(request)
        
        # Remove default delete action (we use soft delete)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        
        # Add soft delete action
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        if 'Moderator' in user_groups or 'Admin' in user_groups or request.user.is_superuser:
            actions['soft_delete_sources'] = (
                self.soft_delete_sources,
                'soft_delete_sources',
                'Mark selected sources as deleted'
            )
            actions['restore_sources'] = (
                self.restore_sources,
                'restore_sources',
                'Restore selected sources'
            )
        
        return actions
    
    def soft_delete_sources(self, request, queryset):
        """
        Bulk action to soft delete sources.
        """
        count = queryset.update(is_deleted=True)
        self.message_user(request, f"{count} source(s) marked as deleted.")
    soft_delete_sources.short_description = "Mark selected sources as deleted"
    
    def restore_sources(self, request, queryset):
        """
        Bulk action to restore soft-deleted sources.
        """
        count = queryset.update(is_deleted=False)
        self.message_user(request, f"{count} source(s) restored.")
    restore_sources.short_description = "Restore selected sources"


# ============================================================================
# User Admin (for moderator restrictions)
# ============================================================================

class CustomUserAdmin(BaseUserAdmin):
    """
    Custom User admin to prevent Moderators from managing other Moderators.
    
    Property 14: Moderators cannot manage other Moderators in Django Admin
    """
    
    def get_queryset(self, request):
        """
        Filter queryset based on user role.
        
        - Admins/Superusers: See all users
        - Moderators: See all users except other Moderators
        - Others: See nothing
        """
        qs = super().get_queryset(request)
        
        # Admins and superusers see everything
        if request.user.is_superuser:
            return qs
        
        # Check user groups
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Admins see everything
        if 'Admin' in user_groups:
            return qs
        
        # Moderators see all users except other Moderators
        if 'Moderator' in user_groups:
            # Exclude users who are in the Moderator group
            moderator_group_users = User.objects.filter(groups__name='Moderator').values_list('id', flat=True)
            return qs.exclude(id__in=moderator_group_users)
        
        # Others see nothing
        return qs.none()
    
    def has_change_permission(self, request, obj=None):
        """
        Check if user can change another user.
        
        - Admins/Superusers: Can change all users
        - Moderators: Cannot change other Moderators
        """
        if not super().has_change_permission(request, obj):
            return False
        
        if obj is None:
            return True
        
        # Admins and superusers can change everything
        if request.user.is_superuser:
            return True
        
        # Check user groups
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Admins can change everything
        if 'Admin' in user_groups:
            return True
        
        # Moderators cannot change other Moderators
        if 'Moderator' in user_groups:
            target_groups = list(obj.groups.values_list('name', flat=True))
            if 'Moderator' in target_groups:
                return False
            return True
        
        return False
    
    def has_delete_permission(self, request, obj=None):
        """
        Check if user can delete another user.
        
        - Admins/Superusers: Can delete users
        - Moderators: Cannot delete other Moderators
        """
        if not super().has_delete_permission(request, obj):
            return False
        
        if obj is None:
            return True
        
        # Admins and superusers can delete
        if request.user.is_superuser:
            return True
        
        # Check user groups
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Admins can delete
        if 'Admin' in user_groups:
            return True
        
        # Moderators cannot delete other Moderators
        if 'Moderator' in user_groups:
            target_groups = list(obj.groups.values_list('name', flat=True))
            if 'Moderator' in target_groups:
                return False
            return True
        
        return False


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ============================================================================
# Admin Site Configuration
# ============================================================================

admin.site.site_header = "Jawafdehi Mgmt"
admin.site.site_title = "Jawafdehi Management Portal"
admin.site.index_title = "Welcome to Jawafdehi Management Portal"
