from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from .models import DocumentSource, JawafEntity
from .rules.predicates import is_admin_or_moderator, is_contributor
import uuid
from datetime import datetime


def index(request):
    return render(request, "index.html")


def docs(request):
    return render(request, "docs.html")


@staff_member_required
@require_http_methods(["GET", "POST"])
def bulk_upload_documents(request):
    """
    View to handle bulk document uploads.
    
    GET: Shows the bulk upload form
    POST: Processes uploaded files and creates new DocumentSource entries
    """
    user = request.user
    
    # Check permissions: only admins, moderators, and contributors can upload
    can_upload = is_admin_or_moderator(user) or is_contributor(user)
    if not can_upload:
        return JsonResponse({'error': 'You do not have permission to upload documents'}, status=403)
    
    if request.method == 'POST':
        # Handle file uploads
        uploaded_files = request.FILES.getlist('documents')
        
        if not uploaded_files:
            return JsonResponse({'error': 'No files uploaded'}, status=400)
        
        created_sources = []
        errors = []
        
        for uploaded_file in uploaded_files:
            try:
                # Generate unique source_id
                timestamp = datetime.now().strftime("%Y%m%d")
                source_id = f"source:{timestamp}:{uuid.uuid4().hex[:8]}"
                
                # Create DocumentSource entry
                doc_source = DocumentSource(
                    source_id=source_id,
                    title=uploaded_file.name.rsplit('.', 1)[0],  # Use filename without extension as title
                    description=f"Uploaded file: {uploaded_file.name}\nFile size: {uploaded_file.size} bytes"
                )
                
                # Save and validate
                doc_source.full_clean()
                doc_source.save()
                
                # Add current user as contributor
                doc_source.contributors.add(user)
                
                created_sources.append({
                    'source_id': source_id,
                    'title': doc_source.title,
                    'filename': uploaded_file.name
                })
            
            except ValidationError as e:
                errors.append({
                    'filename': uploaded_file.name,
                    'error': str(e)
                })
            except Exception as e:
                errors.append({
                    'filename': uploaded_file.name,
                    'error': f'Unexpected error: {str(e)}'
                })
        
        return JsonResponse({
            'success': len(created_sources) > 0,
            'created': created_sources,
            'errors': errors,
            'message': f'Created {len(created_sources)} document source(s)' + (f' with {len(errors)} error(s)' if errors else '')
        })
    
    # GET request - show upload form
    return render(request, 'admin/bulk_upload_documents.html', {
        'title': 'Bulk Upload Documents',
        'opts': DocumentSource._meta,
    })
