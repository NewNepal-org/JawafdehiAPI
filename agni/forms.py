"""
Forms for Agni Django module.

Contains forms for document upload and session management.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import StoredExtractionSession
from .utils import validate_file_type, get_file_validation_error


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading documents to start extraction sessions."""
    
    guidance = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Optional: Provide guidance for AI extraction (e.g., focus areas, context, etc.)'
        }),
        required=False,
        help_text="Optional guidance to help the AI understand what to focus on during extraction."
    )
    
    class Meta:
        model = StoredExtractionSession
        fields = ['document', 'guidance']
        widgets = {
            'document': forms.FileInput(attrs={
                'accept': '.txt,.md,.doc,.docx,.pdf',
                'class': 'form-control'
            })
        }
    
    def clean_document(self):
        """Validate uploaded document file type."""
        document = self.cleaned_data.get('document')
        
        if document:
            error_message = get_file_validation_error(document.name)
            if error_message:
                raise ValidationError(error_message)
        
        return document
    
    def save(self, commit=True):
        """Save the form and store guidance in session_data."""
        instance = super().save(commit=False)
        
        # Store guidance in session_data JSON field
        guidance = self.cleaned_data.get('guidance', '')
        instance.session_data = {'guidance': guidance}
        
        if commit:
            instance.save()
        
        return instance