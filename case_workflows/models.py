"""
Models for tracking case workflow execution.
"""

import uuid

from django.db import models
from django.utils import timezone


class CaseWorkflowRun(models.Model):
    """
    Tracks a single execution of a workflow against a case.

    Each ``(case_id, workflow_id)`` pair is unique — a case can only have
    one run per workflow template.

    The ``case_id`` field is a Jawafdehi ``Case.case_id`` string
    (e.g. ``"case-abc123"``).
    """

    run_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique run identifier (auto-generated UUID)",
    )
    case_id = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Jawafdehi Case.case_id (e.g. case-abc123)",
    )
    workflow_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Workflow template ID (matches directory name under workflows/)",
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
                fields=["case_id", "workflow_id"],
                name="unique_case_workflow",
            )
        ]

    def __str__(self):
        status = "✓" if self.is_complete else ("✗" if self.has_failed else "…")
        return f"[{status}] {self.workflow_id} / {self.case_id}"

    def save(self, *args, **kwargs):
        if not self.run_id:
            self.run_id = f"run-{uuid.uuid4().hex[:12]}"
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

    def get_resume_step(self, workflow) -> str | None:
        """Return the failed step name, or the first non-complete step."""
        steps_state = (self.case_data or {}).get("steps", {})
        for step in workflow.steps:
            if steps_state.get(step.name, {}).get("status") == "failed":
                return step.name
        for step in workflow.steps:
            if steps_state.get(step.name, {}).get("status") != "complete":
                return step.name
        return None

    def can_resume_from(self, step_name: str, workflow) -> tuple[bool, str]:
        """Validate whether this run can resume from the given step."""
        if self.is_complete:
            return False, "Workflow run is already complete"

        step_names = [step.name for step in workflow.steps]
        if step_name not in step_names:
            return False, f"Unknown workflow step: {step_name}"

        step_state = (self.case_data or {}).get("steps", {}).get(step_name, {})
        if step_state.get("status") == "complete":
            return False, f"Step is already complete: {step_name}"

        return True, ""

    def prepare_for_resume(self, step_name: str) -> None:
        """Clear failure fields so the run can execute again."""
        self.has_failed = False
        self.error_message = ""
        self.completed_at = None
        self.save(
            update_fields=["has_failed", "error_message", "completed_at", "updated_at"]
        )
