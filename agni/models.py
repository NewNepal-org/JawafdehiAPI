import uuid
import os
from dataclasses import dataclass
from typing import Optional, List
from django.db import models
from django.contrib.auth.models import User

class TaskStatus(models.TextChoices):
    """Task execution status choices."""
    QUEUED = 'queued', 'Queued'
    RUNNING = 'running', 'Running'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'

@dataclass
class AgniBackgroundTask:
    """Represents a background task running on a session."""
    task_type: str
    task_id: str
    status: str = TaskStatus.QUEUED
    entity_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            'task_type': self.task_type,
            'task_id': self.task_id,
            'status': self.status,
            'entity_id': self.entity_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgniBackgroundTask':
        """Create from dictionary."""
        return cls(
            task_type=data['task_type'],
            task_id=data['task_id'],
            status=data.get('status', TaskStatus.QUEUED),
            entity_id=data.get('entity_id')
        )


class SessionStatus(models.TextChoices):
    """Session processing status choices."""
    PENDING = 'pending', 'Pending'
    PROCESSING_METADATA = 'processing_metadata', 'Processing Metadata'
    METADATA_EXTRACTED = 'metadata_extracted', 'Metadata Extracted'
    PROCESSING_ENTITIES = 'processing_entities', 'Processing Entities'
    AWAITING_REVIEW = 'awaiting_review', 'Awaiting Review'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'



class TaskType(models.TextChoices):
    """Types of tasks that can run on a session."""
    EXTRACT_METADATA = 'extract_metadata', 'Extract Metadata'
    EXTRACT_ENTITIES = 'extract_entities', 'Extract Entities'
    UPDATE_ENTITY = 'update_entity', 'Update Individual Entity'


class StoredExtractionSession(models.Model):
    """Persisted extraction session for resumable workflows."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.FileField(upload_to='agni/documents/')
    session_data = models.JSONField(default=dict, help_text="Serialized AgniExtractionSession data")
    status = models.CharField(max_length=25, choices=SessionStatus.choices, default=SessionStatus.PENDING)
    
    # Task tracking - support for concurrent tasks
    tasks = models.JSONField(default=list, help_text="Currently running tasks as list of AgniBackgroundTask objects")
    error_message = models.TextField(blank=True, help_text="Error message if processing failed")
    progress_info = models.JSONField(default=dict, help_text="Progress tracking information")
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def add_active_task(self, task_type: TaskType, task_id: str, entity_id: Optional[str] = None) -> None:
        """Add a task to the active tasks list."""
        if not self.tasks:
            self.tasks = []
        
        task = AgniBackgroundTask(
            task_type=task_type.value,
            task_id=task_id,
            entity_id=entity_id
        )
        self.tasks.append(task.to_dict())
        self.save(update_fields=['tasks', 'updated_at'])
    
    def remove_active_task(self, task_id: str) -> None:
        """Remove a task from the active tasks list by task_id."""
        if self.tasks:
            self.tasks = [
                task for task in self.tasks
                if task.get('task_id') != task_id
            ]
            self.save(update_fields=['tasks', 'updated_at'])
    
    def has_active_tasks(self) -> bool:
        """Check if session has any active tasks."""
        return bool(self.tasks)
    
    def get_active_tasks(self) -> List[AgniBackgroundTask]:
        """Get list of currently active tasks as AgniBackgroundTask objects."""
        return [AgniBackgroundTask.from_dict(task) for task in self.tasks] if self.tasks else []
    
    def cleanup_document(self) -> None:
        """Delete the uploaded document file from filesystem."""
        if self.document:
            try:
                if os.path.isfile(self.document.path):
                    os.remove(self.document.path)
            except (ValueError, OSError):
                # File doesn't exist or can't be deleted - ignore
                pass
    
    def mark_failed(self, error_message: str) -> None:
        """Mark session as failed and cleanup document."""
        self.status = SessionStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])
        self.cleanup_document()
    
    def mark_completed(self) -> None:
        """Mark session as completed and cleanup document."""
        self.status = SessionStatus.COMPLETED
        self.save(update_fields=['status', 'updated_at'])
        self.cleanup_document()
    
    def delete(self, *args, **kwargs):
        """Override delete to cleanup document file."""
        self.cleanup_document()
        super().delete(*args, **kwargs)
    
    class Meta:
        verbose_name = "Extraction Session"
        verbose_name_plural = "Extraction Sessions"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Session {self.id} - {self.get_status_display()}"


class ApprovedEntityChange(models.Model):
    """Queue of approved entity changes to be applied to NES."""
    
    CHANGE_TYPE_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    
    # Entity identification
    entity_type = models.CharField(max_length=20, help_text="NES entity type")
    entity_sub_type = models.CharField(max_length=50, blank=True, help_text="NES entity sub-type")
    nes_entity_id = models.CharField(max_length=300, blank=True, help_text="NES entity ID for updates")
    
    # Full entity data
    entity_data = models.JSONField(help_text="Complete entity data for NES")
    
    # Audit
    description = models.TextField(blank=True, help_text="Description of the change")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Approved Entity Change"
        verbose_name_plural = "Approved Entity Changes"
        ordering = ['-approved_at']
    
    def __str__(self):
        action = f"{self.get_change_type_display()} {self.entity_type}"
        if self.entity_sub_type:
            action += f" ({self.entity_sub_type})"
        return action


class UploadDocument(StoredExtractionSession):
    """Proxy model for upload document functionality in admin sidebar."""
    
    class Meta:
        proxy = True
        verbose_name = "Upload Document"
        verbose_name_plural = "Upload Document"