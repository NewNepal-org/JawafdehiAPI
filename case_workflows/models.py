"""
Models for tracking case workflow execution.
"""

import uuid

from django.db import models
from django.utils import timezone


class CaseWorkflowRun(models.Model):
    """
    Tracks a single execution of a workflow template against a case.

    Each ``(case_id, workflow_template_id)`` pair is unique — a case can
    only have one run per template.  To re-run, delete/reset the existing
    record.

    The ``case_id`` field is a **generic string identifier** (not a FK),
    because workflows may target external cases (e.g. NGM court-case
    numbers) that don't yet have a corresponding Jawafdehi ``Case`` record.
    """

    workflow_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique run identifier (auto-generated UUID)",
    )
    case_id = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Case identifier (NGM case number, Jawafdehi case_id, etc.)",
    )
    workflow_template_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="ID of the workflow template (matches directory name)",
    )
    case_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of PRD state and runtime metadata",
    )
    work_dir = models.CharField(
        max_length=500,
        blank=True,
        help_text="Absolute path to the working directory for this run",
    )
    is_complete = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the workflow finished successfully",
    )
    has_failed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the workflow terminated with a failure",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error details if has_failed is True",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution started",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution finished (success or failure)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Case Workflow Run"
        verbose_name_plural = "Case Workflow Runs"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["case_id", "workflow_template_id"],
                name="unique_case_workflow_template",
            )
        ]

    def __str__(self):
        status = "✓" if self.is_complete else ("✗" if self.has_failed else "…")
        return f"[{status}] {self.workflow_template_id} / {self.case_id}"

    def save(self, *args, **kwargs):
        if not self.workflow_id:
            self.workflow_id = f"run-{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)

    def mark_started(self):
        """Record that execution has begun."""
        self.started_at = timezone.now()
        self.save(update_fields=["started_at", "updated_at"])

    def mark_complete(self, case_data: dict | None = None):
        """Record successful completion."""
        self.is_complete = True
        self.has_failed = False
        self.completed_at = timezone.now()
        if case_data is not None:
            self.case_data = case_data
        self.save(
            update_fields=[
                "is_complete",
                "has_failed",
                "completed_at",
                "case_data",
                "updated_at",
            ]
        )

    def mark_failed(self, error_message: str = "", case_data: dict | None = None):
        """Record a failure."""
        self.has_failed = True
        self.is_complete = False
        self.error_message = error_message
        self.completed_at = timezone.now()
        if case_data is not None:
            self.case_data = case_data
        self.save(
            update_fields=[
                "is_complete",
                "has_failed",
                "error_message",
                "completed_at",
                "case_data",
                "updated_at",
            ]
        )
