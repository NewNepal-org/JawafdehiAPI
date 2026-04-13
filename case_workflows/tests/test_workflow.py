"""
Tests for workflow registry and ABC contract.
"""

import re

import pytest

from case_workflows.output import _utc_timestamp
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
        assert step.required_outputs == {}
        assert step.retries == 0

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

    def test_utc_timestamp_format(self):
        ts = _utc_timestamp()
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", ts)


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

    def test_draft_steps_require_expected_artifacts(self):
        wf = get_workflow("ciaa_caseworker")
        draft_step = next(s for s in wf.steps if s.name == "draft-case")
        review_step = next(s for s in wf.steps if s.name == "review-draft")
        revise_step = next(s for s in wf.steps if s.name == "revise-draft")

        assert draft_step.required_outputs == {"draft.md": 100}
        assert review_step.required_outputs == {"draft-review.md": 100}
        assert revise_step.required_outputs == {"draft.md": 100}
        assert draft_step.retries == 1

    def test_draft_prompt_requires_immediate_file_creation(self, tmp_path):
        wf = get_workflow("ciaa_caseworker")
        case_dir = tmp_path / "081-CR-0123"
        step = next(s for s in wf.steps if s.name == "draft-case")

        prompt = step.prompt_fn(case_dir)

        assert "Create" in prompt
        assert "draft.md immediately" in prompt
        assert "core sources first" in prompt

    def test_create_case_step_has_filtered_tools(self):
        wf = get_workflow("ciaa_caseworker")
        create_case = next(s for s in wf.steps if s.name == "create-case")
        assert create_case.mcp_tool_filter is not None
        tools = set(create_case.mcp_tool_filter)
        assert {
            "create_jawafdehi_case",
            "patch_jawafdehi_case",
            "get_jawafdehi_case",
            "search_jawafdehi_cases",
            "search_jawaf_entities",
            "get_jawaf_entity",
            "create_jawaf_entity",
            "upload_document_source",
        }.issubset(tools)

    def test_instructions_dir_exists(self):
        wf = get_workflow("ciaa_caseworker")
        idir = wf.get_instructions_dir()
        assert idir.is_dir()
        assert (idir / "INSTRUCTIONS.md").exists()

    def test_fetch_news_prompt_limits_article_count(self, tmp_path):
        wf = get_workflow("ciaa_caseworker")
        case_dir = tmp_path / "081-CR-0123"
        step = next(s for s in wf.steps if s.name == "fetch-news-articles")

        prompt = step.prompt_fn(case_dir)

        assert "Collect 6-10 high-quality, case-relevant news articles" in prompt
        assert "Do not collect more than 10 articles" in prompt

    def test_fetch_news_prompt_requires_parallel_batches(self, tmp_path):
        wf = get_workflow("ciaa_caseworker")
        case_dir = tmp_path / "081-CR-0123"
        step = next(s for s in wf.steps if s.name == "fetch-news-articles")

        prompt = step.prompt_fn(case_dir)

        assert "generate all required query variations up front" in prompt
        assert "balanced parallel batches of 6-8 URLs" in prompt
        assert "run `convert_to_markdown` in parallel for that batch" in prompt

    def test_update_case_prompt_requires_original_news_urls(self, tmp_path):
        wf = get_workflow("ciaa_caseworker")
        case_dir = tmp_path / "081-CR-0123"
        step = next(s for s in wf.steps if s.name == "update-case-details")

        prompt = step.prompt_fn(case_dir)

        assert 'url: ["<original_article_url>"]' in prompt
        assert "Do not use the uploaded markdown path as the external URL" in prompt
        assert "source descriptions are generally in Nepali" in prompt

    def test_instructions_define_news_limit_and_tag_guidance(self):
        wf = get_workflow("ciaa_caseworker")
        instructions = (wf.get_instructions_dir() / "INSTRUCTIONS.md").read_text()

        assert "6 to 10 high-quality articles total" in instructions
        assert "Do **not** collect more than 10 news articles" in instructions
        assert "fetch promising URLs in batches of 6 to 8" in instructions
        assert "Run the planned query wave" in instructions
        assert "### Recommended tags" in instructions
        assert "`CIAA`" in instructions
