"""
Agni API views for document processing and entity extraction.

Provides REST endpoints for:
- Document upload and session creation
- Session status monitoring
- Entity resolution (match, create, skip)
- Conversation management
- Change persistence
"""

import re
from typing import Optional

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from django_q.tasks import async_task

from cases.rules.predicates import is_admin
from nes.core.identifiers.validators import is_valid_entity_id
from .models import StoredExtractionSession, SessionStatus, TaskType, AgniBackgroundTask, ApprovedEntityChange
from .utils import deserialize_session, serialize_session


class IsAdmin(BasePermission):
    """
    Custom permission class using the is_admin predicate from cases.rules.predicates.
    
    Allows access only to users who are:
    - Superusers, OR
    - Members of the 'Admin' group
    """
    
    def has_permission(self, request, view):
        return bool(request.user and is_admin(request.user))


@api_view(['POST'])
@permission_classes([IsAdmin])
@transaction.atomic
def create_session(request):
    """
    Upload document and create extraction session.
    
    POST /api/agni/sessions/
    Content-Type: multipart/form-data
    
    Request:
    - document: File (.txt, .md, .doc, .docx, .pdf)
    - guidance: Optional[str]
    
    Response: 201 Created
    {
        "id": "uuid",
        "status": "pending",
        "document_url": "/media/agni/documents/file.pdf",
        "created_at": "2024-12-18T10:00:00Z"
    }
    """
    # Validate document file
    if 'document' not in request.FILES:
        return Response(
            {
                "success": False,
                "error": "validation_error",
                "message": "Document file required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    document = request.FILES['document']
    guidance = request.data.get('guidance', '')
    
    # Validate file type
    allowed_extensions = ['.txt', '.md', '.doc', '.docx', '.pdf']
    if not any(document.name.lower().endswith(ext) for ext in allowed_extensions):
        return Response(
            {
                "success": False,
                "error": "validation_error",
                "message": f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create session with guidance and document path in session_data
    session = StoredExtractionSession.objects.create(
        document=document,
        session_data={
            'guidance': guidance,
            'document': None  # Will be set after save
        },
        created_by=request.user,
        status=SessionStatus.PENDING
    )
    
    # Update session_data with the actual document path after the file is saved
    session.session_data['document'] = session.document.path
    session.save(update_fields=['session_data'])
    
    # Auto-trigger metadata extraction task
    task_id = async_task('agni.tasks.extract_metadata_task', session_id=str(session.id))
    session.add_active_task(TaskType.EXTRACT_METADATA, task_id)
    
    return Response({
        "id": str(session.id),
        "status": session.status,
        "document_url": session.document.url,
        "created_at": session.created_at.isoformat()
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAdmin])
def get_session(request, session_id):
    """
    Get session status and details.
    
    GET /api/agni/sessions/{session_id}/
    
    Response:
    {
        "id": "uuid",
        "status": "processing_entities",
        "tasks": [
            {"task_type": "extract_entities", "task_id": "task_123", "entity_id": null}
        ],
        "error_message": null,
        "progress": {"current": 3, "total": 10, "stage": "extracting_entities"},
        "metadata": {...},
        "entities": [...],
        "updated_at": "2024-12-18T10:30:00Z"
    }
    """
    session = get_object_or_404(StoredExtractionSession, id=session_id)
    
    # Deserialize session data to get metadata and entities
    agni_session = deserialize_session(session.session_data)
    
    response_data = {
        "id": str(session.id),
        "status": session.status,
        # Canonical key (backed by StoredExtractionSession.tasks JSONField)
        "tasks": [task.to_dict() for task in session.get_active_tasks()],
        # Backward-compatible alias (deprecated): remove once clients migrate
        "active_tasks": [task.to_dict() for task in session.get_active_tasks()],
        "error_message": session.error_message,
        "progress": session.progress_info,
        "metadata": None,
        "entities": [],
        "updated_at": session.updated_at.isoformat()
    }
    
    # Add metadata if available
    if hasattr(agni_session, 'metadata') and agni_session.metadata:
        response_data["metadata"] = {
            "title": getattr(agni_session.metadata, 'title', None),
            "summary": getattr(agni_session.metadata, 'summary', None),
            "author": getattr(agni_session.metadata, 'author', None),
            "publication_date": (
                agni_session.metadata.publication_date.isoformat() 
                if hasattr(agni_session.metadata, 'publication_date') and agni_session.metadata.publication_date 
                else None
            ),
            "document_type": getattr(agni_session.metadata, 'document_type', None),
            "source": getattr(agni_session.metadata, 'source', None)
        }
    
    # Add entities if available
    if hasattr(agni_session, 'entities') and agni_session.entities:
        response_data["entities"] = [
            {
                "entity_type": getattr(entity.entity_type, 'value', str(entity.entity_type)),
                "entity_sub_type": (
                    getattr(entity.entity_sub_type, 'value', str(entity.entity_sub_type)) 
                    if hasattr(entity, 'entity_sub_type') and entity.entity_sub_type 
                    else None
                ),
                "names": getattr(entity, 'names', []),
                "entity_data": getattr(entity, 'entity_data', {}),
                "confidence": getattr(entity, 'confidence', 0.0),
                "status": getattr(entity, 'status', 'unknown'),
                "candidates": [
                    {
                        "nes_id": getattr(candidate, 'nes_id', ''),
                        "confidence": getattr(candidate, 'confidence', 0.0),
                        "reason": getattr(candidate, 'reason', '')
                    }
                    for candidate in getattr(entity, 'candidates', [])
                ],
                "matched_id": getattr(entity, 'matched_id', None),
                "needs_creation": getattr(entity, 'needs_creation', False)
            }
            for entity in agni_session.entities
        ]
    
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAdmin])
@transaction.atomic
def resolve_entity(request, session_id, entity_index):
    """
    Resolve entity (match, create, or skip).
    
    POST /api/agni/sessions/{session_id}/entities/{entity_index}/
    
    Request (Match to existing):
    {
        "action": "match",
        "nes_id": "person_123"
    }
    
    Request (Create new):
    {
        "action": "create",
        "confirmed": true
    }
    
    Request (Skip entity):
    {
        "action": "skip",
        "reason": "Not relevant to case"
    }
    
    Response:
    {
        "success": true,
        "entity_status": "matched" | "create_new" | "skipped"
    }
    """
    session = get_object_or_404(StoredExtractionSession, id=session_id)
    
    # Validate session status
    if session.status != SessionStatus.AWAITING_REVIEW:
        return Response(
            {
                "success": False,
                "error": "invalid_state",
                "message": "Session must be in awaiting_review status"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Deserialize session data and validate entity_index
    agni_session = deserialize_session(session.session_data)
    if not hasattr(agni_session, 'entities') or entity_index < 0 or entity_index >= len(agni_session.entities):
        return Response({
            "success": False, 
            "error": "validation_error", 
            "message": "Invalid entity index"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    action = request.data.get('action')
    
    if action == 'match':
        nes_id = request.data.get('nes_id')
        if not nes_id:
            return Response(
                {
                    "success": False,
                    "error": "validation_error",
                    "message": "nes_id required for match action"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get entity for validation
        entity = agni_session.entities[entity_index]
        entity_type = getattr(entity.entity_type, 'value', str(entity.entity_type))
        
        # Validate NES ID format
        if not is_valid_entity_id(nes_id, entity_type):
            return Response(
                {
                    "success": False,
                    "error": "validation_error",
                    "message": "Invalid NES entity ID format"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update entity in session_data
        entity.matched_id = nes_id
        entity.needs_creation = False
        if hasattr(entity, 'is_skipped'):
            entity.is_skipped = False
        entity_status = "matched"
        
    elif action == 'create':
        confirmed = request.data.get('confirmed', False)
        if not confirmed:
            return Response(
                {
                    "success": False,
                    "error": "validation_error",
                    "message": "confirmed=true required for create action"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark entity for creation in session_data
        entity = agni_session.entities[entity_index]
        entity.needs_creation = True
        entity.matched_id = None
        if hasattr(entity, 'is_skipped'):
            entity.is_skipped = False
        entity_status = "create_new"
        
    elif action == 'skip':
        reason = request.data.get('reason', '')
        # Mark entity as skipped in session_data
        entity = agni_session.entities[entity_index]
        entity.is_skipped = True
        entity.skip_reason = reason
        entity.matched_id = None
        entity.needs_creation = False
        entity_status = "skipped"
        
    else:
        return Response(
            {
                "success": False,
                "error": "validation_error",
                "message": "action must be 'match', 'create', or 'skip'"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Save updated session_data
    session.session_data = serialize_session(agni_session)
    session.save(update_fields=['session_data', 'updated_at'])
    
    return Response({
        "success": True,
        "entity_status": entity_status
    })


@api_view(['DELETE'])
@permission_classes([IsAdmin])
@transaction.atomic
def delete_entity(request, session_id, entity_index):
    """
    Delete entity from session.
    
    DELETE /api/agni/sessions/{session_id}/entities/{entity_index}/delete/
    
    Response:
    {
        "success": true,
        "message": "Entity deleted successfully"
    }
    """
    session = get_object_or_404(StoredExtractionSession, id=session_id)
    
    # Validate session status
    if session.status != SessionStatus.AWAITING_REVIEW:
        return Response(
            {
                "success": False,
                "error": "invalid_state",
                "message": "Session must be in awaiting_review status"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Deserialize session data and validate entity_index
    agni_session = deserialize_session(session.session_data)
    if not hasattr(agni_session, 'entities') or entity_index < 0 or entity_index >= len(agni_session.entities):
        return Response({
            "success": False, 
            "error": "validation_error", 
            "message": "Invalid entity index"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get entity name for logging
    entity = agni_session.entities[entity_index]
    entity_name = "Unknown"
    if hasattr(entity, 'names') and entity.names:
        entity_name = entity.names[0] if isinstance(entity.names[0], str) else getattr(entity.names[0], 'name', 'Unknown')
    
    # Remove entity from the list
    agni_session.entities.pop(entity_index)
    
    # Update progress info if it exists
    if session.progress_info and 'total_entities' in session.progress_info:
        session.progress_info['total_entities'] = len(agni_session.entities)
        # Recalculate other progress metrics
        if hasattr(agni_session, 'entities'):
            needs_disambiguation = sum(1 for e in agni_session.entities if getattr(e, 'status', '') == 'needs_disambiguation')
            auto_matched = sum(1 for e in agni_session.entities if getattr(e, 'status', '') == 'auto_matched')
            session.progress_info['needs_disambiguation'] = needs_disambiguation
            session.progress_info['auto_matched'] = auto_matched
    
    # Save updated session_data
    session.session_data = serialize_session(agni_session)
    session.save(update_fields=['session_data', 'progress_info', 'updated_at'])
    
    return Response({
        "success": True,
        "message": f"Entity '{entity_name}' deleted successfully"
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
@transaction.atomic
def post_conversation_message(request, session_id, conversation_key):
    """
    Post message to conversation thread.
    
    POST /api/agni/sessions/{session_id}/conversations/{conversation_key}/
    
    Request:
    {
        "message": "Please extract more person names"
    }
    
    Response:
    {
        "success": true,
        "message_id": "msg_123"
    }
    
    Conversation Keys:
    - "metadata_extraction"
    - "entity_extraction"
    - "entity:0", "entity:1", ... (per-entity conversations)
    """
    session = get_object_or_404(StoredExtractionSession, id=session_id)
    
    message = request.data.get('message')
    if not message:
        return Response(
            {
                "success": False,
                "error": "validation_error",
                "message": "message required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate conversation key
    valid_keys = ['metadata_extraction', 'entity_extraction']
    if conversation_key.startswith('entity:'):
        try:
            entity_index = int(conversation_key.split(':')[1])
            # Validate entity_index against session entities
            agni_session = deserialize_session(session.session_data)
            if not hasattr(agni_session, 'entities') or entity_index < 0 or entity_index >= len(agni_session.entities):
                raise ValueError("Invalid entity index")
        except (ValueError, IndexError):
            return Response(
                {
                    "success": False,
                    "error": "validation_error",
                    "message": "Invalid conversation key"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    elif conversation_key not in valid_keys:
        return Response(
            {
                "success": False,
                "error": "validation_error",
                "message": "Invalid conversation key"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Add message to conversation and potentially trigger UPDATE_ENTITY task
    if conversation_key.startswith('entity:'):
        entity_index = int(conversation_key.split(':')[1])
        task_id = async_task('agni.tasks.update_entity_task', session_id=str(session_id), entity_index=entity_index, message=message)
        session.add_active_task(TaskType.UPDATE_ENTITY, task_id, entity_index)
    
    message_id = f"msg_{session_id}_{conversation_key}_{len(session.session_data.get('conversations', {}).get(conversation_key, []))}"
    
    return Response({
        "success": True,
        "message_id": message_id
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
@transaction.atomic
def persist_changes(request, session_id):
    """
    Persist approved entity changes (synchronous operation).
    
    POST /api/agni/sessions/{session_id}/persist/
    
    Request:
    {
        "description": "Extracted from corruption case document",
        "confirm": true
    }
    
    Response:
    {
        "success": true,
        "change_ids": ["change_abc", "change_def"],
        "message": "2 changes persisted successfully"
    }
    """
    session = get_object_or_404(StoredExtractionSession, id=session_id)
    
    # Validate session status
    if session.status != SessionStatus.AWAITING_REVIEW:
        return Response(
            {
                "success": False,
                "error": "invalid_state",
                "message": "Session must be in awaiting_review status"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    description = request.data.get('description', '')
    confirm = request.data.get('confirm', False)
    
    if not confirm:
        return Response(
            {
                "success": False,
                "error": "validation_error",
                "message": "confirm=true required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Deserialize session data and validate all entities are resolved
    agni_session = deserialize_session(session.session_data)
    
    if not hasattr(agni_session, 'entities'):
        return Response({
            "success": False,
            "error": "validation_error",
            "message": "No entities found in session"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    for i, entity in enumerate(agni_session.entities):
        entity_status = getattr(entity, 'status', 'unknown')
        if entity_status not in ('matched', 'create_new', 'skipped'):
            return Response({
                "success": False,
                "error": "validation_error",
                "message": f"Entity {i} not resolved: {entity_status}"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Synchronously create ApprovedEntityChange records
    change_ids = []
    for entity in agni_session.entities:
        entity_status = getattr(entity, 'status', 'unknown')
        if entity_status in ('matched', 'create_new'):
            change_type = 'update' if entity_status == 'matched' else 'create'
            entity_type = getattr(entity.entity_type, 'value', str(entity.entity_type))
            entity_sub_type = (
                getattr(entity.entity_sub_type, 'value', str(entity.entity_sub_type))
                if hasattr(entity, 'entity_sub_type') and entity.entity_sub_type
                else ''
            )
            
            change = ApprovedEntityChange.objects.create(
                change_type=change_type,
                entity_type=entity_type,
                entity_sub_type=entity_sub_type,
                nes_entity_id=getattr(entity, 'matched_id', '') or '',
                entity_data=getattr(entity, 'entity_data', {}),
                description=description,
                approved_by=request.user
            )
            change_ids.append(str(change.id))
    
    # Mark session as completed (this will also cleanup the document)
    session.mark_completed()
    
    # Count actual changes (skip skipped entities)
    change_count = len(change_ids)
    
    return Response({
        "success": True,
        "change_ids": change_ids,
        "message": f"{change_count} changes persisted successfully"
    })
