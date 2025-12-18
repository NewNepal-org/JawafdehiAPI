"""
URL configuration for Agni API endpoints.

Provides REST API routes for document processing and entity extraction.
"""

from django.urls import path
from . import views

app_name = 'agni'

urlpatterns = [
    # Session management
    path('sessions/', views.create_session, name='create_session'),
    path('sessions/<uuid:session_id>/', views.get_session, name='get_session'),
    
    # Entity resolution
    path('sessions/<uuid:session_id>/entities/<int:entity_index>/', 
         views.resolve_entity, name='resolve_entity'),
    
    # Entity deletion
    path('sessions/<uuid:session_id>/entities/<int:entity_index>/delete/', 
         views.delete_entity, name='delete_entity'),
    
    # Conversation management
    path('sessions/<uuid:session_id>/conversations/<str:conversation_key>/', 
         views.post_conversation_message, name='post_conversation_message'),
    
    # Change persistence
    path('sessions/<uuid:session_id>/persist/', 
         views.persist_changes, name='persist_changes'),
]