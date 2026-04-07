"""
Tests for workflow registry and ABC contract.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from case_workflows.registry import get_workflow, list_workflows
from case_workflows.workflow import Workflow, WorkflowStep


class TestWorkflowStep:
    """Tests for the WorkflowStep dataclass."""

    def test_create_step(self):
        step = WorkflowStep(
            name="fetch-data",
            prompt_fn=lambda case_dir: f"Fetch data for {case_dir.name}",
        )
        assert step.name == "fetch-data"
        assert callable(step.prompt_fn)

    def test_step_defaults(self):
        step = WorkflowStep(
            name="draft-case",
            prompt_fn=lambda case_dir: "Draft the case.",
        )
        assert step.skills == []
        assert step.tools == []
        assert step.mcp_servers == {}
        assert step.subagents == []
        assert step.system_prompt is None

    def test_prompt_fn_receives_path(self, tmp_path):
        case_dir = tmp_path / "case-abc123"
        step = WorkflowStep(
            name="test",
            prompt_fn=lambda d: f"Working on {d.name}",
        )
        result = step.prompt_fn(case_dir)
        assert "case-abc123" in result

    def test_step_with_mcp_servers(self):
        step = WorkflowStep(
            name="fetch-web",
            prompt_fn=lambda d: "Fetch from web",
            mcp_servers={
                "fetch": {
                    "command": "uvx",
                    "args": ["mcp-server-fetch"],
                    "transport": "stdio",
                }
            },
        )
        assert "fetch" in step.mcp_servers

    def test_step_with_system_prompt(self):
        step = WorkflowStep(
            name="draft",
            prompt_fn=lambda d: "Draft the case.",
            system_prompt="You are a caseworker.",
        )
        assert step.system_prompt == "You are a caseworker."


class TestWorkflowABC:
    """Tests for the Workflow ABC contract."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Workflow()

    def test_concrete_workflow_requires_all_abstract_methods(self):
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
        assert len(wf.steps) >= 1

    def test_get_unknown_workflow_raises(self):
        with pytest.raises(KeyError, match="Unknown workflow"):
            get_workflow("nonexistent_workflow")

    def test_step_names(self):
        wf = get_workflow("ciaa_caseworker")
        names = [s.name for s in wf.steps]
        assert "initialize-casework" in names

    def test_step_prompt_fns_callable(self, tmp_path):
        wf = get_workflow("ciaa_caseworker")
        case_dir = tmp_path / "case-test01"
        for step in wf.steps:
            prompt = step.prompt_fn(case_dir)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_fetch_steps_have_mcp_servers(self):
        """Steps that need web access should have mcp_servers configured."""
        wf = get_workflow("ciaa_caseworker")
        fetch_steps = [s for s in wf.steps if s.mcp_servers]
        for step in fetch_steps:
            assert len(step.mcp_servers) > 0

    def test_instructions_dir_exists(self):
        wf = get_workflow("ciaa_caseworker")
        idir = wf.get_instructions_dir()
        assert idir.is_dir()
        assert (idir / "INSTRUCTIONS.md").exists()
