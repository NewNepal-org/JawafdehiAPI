"""
Tests for the CaseWorkflowRun model.
"""

import pytest
from django.db import IntegrityError

from case_workflows.models import CaseWorkflowRun


@pytest.mark.django_db
class TestCaseWorkflowRunModel:
    """Tests for CaseWorkflowRun CRUD and lifecycle."""

    def test_create_run(self):
        """A run can be created with minimal fields."""
        run = CaseWorkflowRun.objects.create(
            case_id="case-abc123",
            workflow_id="ciaa_caseworker",
        )
        assert run.run_id.startswith("run-")
        assert run.case_id == "case-abc123"
        assert run.workflow_id == "ciaa_caseworker"
        assert not run.is_complete
        assert not run.has_failed
        assert run.case_data == {}

    def test_auto_generates_run_id(self):
        """run_id is auto-generated on save if not set."""
        run = CaseWorkflowRun(
            case_id="case-def456",
            workflow_id="ciaa_caseworker",
        )
        assert not run.run_id
        run.save()
        assert run.run_id.startswith("run-")
        assert len(run.run_id) == 16  # "run-" + 12 hex chars

    def test_unique_case_workflow_constraint(self):
        """Cannot create two runs for the same case + workflow."""
        CaseWorkflowRun.objects.create(
            case_id="case-abc123",
            workflow_id="ciaa_caseworker",
        )
        with pytest.raises(IntegrityError):
            CaseWorkflowRun.objects.create(
                case_id="case-abc123",
                workflow_id="ciaa_caseworker",
            )

    def test_different_workflows_same_case(self):
        """Same case can have runs for different workflows."""
        run1 = CaseWorkflowRun.objects.create(
            case_id="case-abc123",
            workflow_id="ciaa_caseworker",
        )
        run2 = CaseWorkflowRun.objects.create(
            case_id="case-abc123",
            workflow_id="other_workflow",
        )
        assert run1.pk != run2.pk

    def test_mark_started(self):
        """mark_started sets started_at timestamp."""
        run = CaseWorkflowRun.objects.create(
            case_id="case-ghi789",
            workflow_id="ciaa_caseworker",
        )
        assert run.started_at is None
        run.mark_started()
        run.refresh_from_db()
        assert run.started_at is not None

    def test_mark_complete(self):
        """mark_complete sets is_complete and completed_at."""
        run = CaseWorkflowRun.objects.create(
            case_id="case-ghi789",
            workflow_id="ciaa_caseworker",
        )
        prd_data = {"is_complete": True, "userStories": []}
        run.mark_complete(case_data=prd_data)
        run.refresh_from_db()

        assert run.is_complete is True
        assert run.has_failed is False
        assert run.completed_at is not None
        assert run.case_data == prd_data

    def test_mark_failed(self):
        """mark_failed sets has_failed with error message."""
        run = CaseWorkflowRun.objects.create(
            case_id="case-ghi789",
            workflow_id="ciaa_caseworker",
        )
        run.mark_failed(error_message="Agent CLI crashed")
        run.refresh_from_db()

        assert run.has_failed is True
        assert run.is_complete is False
        assert run.error_message == "Agent CLI crashed"
        assert run.completed_at is not None

    def test_str_representation(self):
        """__str__ shows status icon, workflow, and case."""
        run = CaseWorkflowRun(
            case_id="case-abc123",
            workflow_id="ciaa_caseworker",
        )
        assert "…" in str(run)  # in-progress
        assert "ciaa_caseworker" in str(run)
        assert "case-abc123" in str(run)

        run.is_complete = True
        assert "✓" in str(run)

        run.is_complete = False
        run.has_failed = True
        assert "✗" in str(run)
