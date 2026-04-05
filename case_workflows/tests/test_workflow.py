"""
Tests for workflow registry and ABC contract.
"""

import pytest

from case_workflows.registry import get_workflow, list_workflows
from case_workflows.workflow import Workflow, WorkflowStep


class TestWorkflowStep:
    """Tests for the WorkflowStep dataclass."""

    def test_create_step(self):
        step = WorkflowStep(
            id="US-001",
            title="Initialize",
            description="Setup directories",
            priority=1,
            acceptance_criteria=["Folder exists", "Log written"],
        )
        assert step.id == "US-001"
        assert step.title == "Initialize"
        assert len(step.acceptance_criteria) == 2

    def test_step_defaults(self):
        step = WorkflowStep(
            id="US-002",
            title="Fetch Data",
            description="Get data",
            priority=2,
        )
        assert step.acceptance_criteria == []


class TestWorkflowABC:
    """Tests for the Workflow ABC contract."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Workflow()

    def test_concrete_workflow_requires_all_methods(self):
        """A subclass missing required abstract methods cannot be instantiated."""

        class IncompleteWorkflow(Workflow):
            @property
            def workflow_id(self):
                return "test"

        with pytest.raises(TypeError):
            IncompleteWorkflow()


class TestWorkflowRegistry:
    """Tests for workflow auto-discovery and registration."""

    def test_ciaa_caseworker_registered(self):
        """The ciaa_caseworker template should be auto-discovered."""
        wids = list_workflows()
        assert "ciaa_caseworker" in wids

    def test_get_workflow(self):
        wf = get_workflow("ciaa_caseworker")
        assert wf.workflow_id == "ciaa_caseworker"
        assert wf.display_name == "CIAA Caseworker"
        assert len(wf.steps) == 6

    def test_get_unknown_workflow_raises(self):
        with pytest.raises(KeyError, match="Unknown workflow"):
            get_workflow("nonexistent_workflow")

    def test_prd_template_loads(self):
        wf = get_workflow("ciaa_caseworker")
        prd = wf.get_prd()
        assert "userStories" in prd
        assert prd["project"] == "Jawafdehi"

    def test_instructions_dir_exists(self):
        wf = get_workflow("ciaa_caseworker")
        idir = wf.get_instructions_dir()
        assert idir.is_dir()
        assert (idir / "INSTRUCTIONS.md").exists()
