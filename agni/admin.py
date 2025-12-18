from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.conf import settings
from .models import StoredExtractionSession, ApprovedEntityChange, UploadDocument
from .forms import DocumentUploadForm


@admin.register(UploadDocument)
class UploadDocumentAdmin(admin.ModelAdmin):
    """Proxy admin for upload document functionality in sidebar."""
    
    def has_module_permission(self, request):
        """Show in admin sidebar."""
        return True
    
    def has_add_permission(self, request):
        """Allow access to upload view."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow access to upload view."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """No delete permission needed."""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Redirect to upload view."""
        return HttpResponseRedirect(reverse('admin:agni_storedextractionsession_upload'))
    
    def add_view(self, request, form_url='', extra_context=None):
        """Redirect to upload view."""
        return HttpResponseRedirect(reverse('admin:agni_storedextractionsession_upload'))


@admin.register(StoredExtractionSession)
class StoredExtractionSessionAdmin(admin.ModelAdmin):
    """Admin interface for StoredExtractionSession model."""
    
    list_display = ['id', 'document', 'status', 'created_by', 'created_at', 'updated_at', 'processing_session_link']
    list_filter = ['status', 'created_by', 'created_at']
    search_fields = ['document', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processing_session_link']
    ordering = ['-updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('id', 'document', 'status', 'processing_session_link')
        }),
        ('Session Data', {
            'fields': ('session_data',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def processing_session_link(self, obj):
        """Generate link to document processing session."""
        if obj.id:
            url = reverse('admin:agni_storedextractionsession_upload') + f'?session_id={obj.id}'
            return format_html('<a href="{}" target="_blank">View Processing Session</a>', url)
        return '-'
    processing_session_link.short_description = 'Processing Session'
    processing_session_link.allow_tags = True
    
    def get_urls(self):
        """Add custom URLs for document upload."""
        urls = super().get_urls()
        custom_urls = [
            path('upload/', self.admin_site.admin_view(self.upload_document_view), name='agni_storedextractionsession_upload'),
        ]
        return custom_urls + urls
    
    def upload_document_view(self, request):
        """Custom view for document upload with validation."""
        # Only handle GET requests - let JavaScript handle the upload via API
        if request.method == 'POST':
            # This shouldn't happen with our AJAX approach, but just in case
            messages.error(request, 'Please use the upload button on the page.')
            return HttpResponseRedirect(request.path)
        
        # Get proper admin context for the upload page
        context = {
            'title': 'Upload Document for AI Processing',
            'opts': self.model._meta,
            'has_view_permission': True,
            'has_add_permission': True,
            'site_title': self.admin_site.site_title,
            'site_header': self.admin_site.site_header,
            'site_url': self.admin_site.site_url,
            'has_permission': True,
            'available_apps': self.admin_site.get_app_list(request),
            'is_popup': False,
            'is_nav_sidebar_enabled': True,
            'agni_ui_debug_url': getattr(settings, 'AGNI_UI_DEBUG_URL', None),
        }
        
        return TemplateResponse(request, 'admin/agni/upload_document.html', context)
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist to add upload button."""
        extra_context = extra_context or {}
        extra_context['upload_url'] = reverse('admin:agni_storedextractionsession_upload')
        return super().changelist_view(request, extra_context)


@admin.register(ApprovedEntityChange)
class ApprovedEntityChangeAdmin(admin.ModelAdmin):
    """Admin interface for ApprovedEntityChange model."""
    
    list_display = ['id', 'change_type', 'entity_type', 'entity_sub_type', 'approved_by', 'approved_at']
    list_filter = ['change_type', 'entity_type', 'entity_sub_type', 'approved_by', 'approved_at']
    search_fields = ['entity_type', 'entity_sub_type', 'nes_entity_id', 'description']
    readonly_fields = ['id', 'approved_at']
    ordering = ['-approved_at']
    
    fieldsets = (
        (None, {
            'fields': ('id', 'change_type', 'entity_type', 'entity_sub_type', 'nes_entity_id')
        }),
        ('Entity Data', {
            'fields': ('entity_data',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('description', 'approved_by', 'approved_at')
        }),
    )