"""
Tests for Workflow execution methods (setup_work_dir, initialize).

These tests exercise the execution logic that was formerly in WorkflowRunner,
now merged directly into the Workflow ABC.
"""

import json
import shutil
from unittest.mock import patch

import pytest

from case_workflows.models import CaseWorkflowRun
from case_workflows.registry import get_workflow


@pytest.mark.django_db
class TestWorkflowSetupWorkDir:
    """Tests for Workflow.setup_work_dir()."""

    def _make_run(self, case_id="case-testcase01"):
        return CaseWorkflowRun.objects.create(
            case_id=case_id,
            workflow_id="ciaa_caseworker",
        )

    def test_setup_creates_base_files(self, tmp_path, settings):
        """setup_work_dir creates dir with prd.json and progress.json."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()

        work_dir = workflow.setup_work_dir(run)

        assert work_dir.is_dir()
        assert (work_dir / "prd.json").is_file()
        assert (work_dir / "progress.json").is_file()

        run.refresh_from_db()
        assert run.work_dir == str(work_dir)

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_calls_workflow_hook(self, tmp_path, settings):
        """on_work_dir_created is called — for CIAA this creates sources/ dirs."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()

        work_dir = workflow.setup_work_dir(run)

        assert (work_dir / "sources" / "raw").is_dir()
        assert (work_dir / "sources" / "markdown").is_dir()

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_progress_json_is_valid(self, tmp_path, settings):
        """progress.json starts with expected schema."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()

        work_dir = workflow.setup_work_dir(run)
        import json

        data = json.loads((work_dir / "progress.json").read_text())
        assert data["is_complete"] is False
        assert data["progress"] == []
        assert isinstance(data["files"], dict)

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_prd_is_valid_json(self, tmp_path, settings):
        """prd.json contains the template PRD data."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()

        work_dir = workflow.setup_work_dir(run)
        with open(work_dir / "prd.json") as f:
            prd = json.load(f)

        assert prd["project"] == "Jawafdehi"
        assert "userStories" in prd

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_work_dir_path_structure(self, tmp_path, settings):
        """Work dir follows <base>/<workflow_id>/<case_id>/ pattern."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run(case_id="case-abc123")

        work_dir = workflow.setup_work_dir(run)

        assert work_dir == tmp_path / "ciaa_caseworker" / "case-abc123"

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_deletes_existing_dir(self, tmp_path, settings):
        """If the work dir already exists it is deleted and recreated."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()

        work_dir1 = workflow.setup_work_dir(run)
        marker = work_dir1 / "marker.txt"
        marker.write_text("hello")

        work_dir2 = workflow.setup_work_dir(run)
        assert work_dir1 == work_dir2
        assert not marker.exists()
        assert (work_dir2 / "prd.json").exists()

        shutil.rmtree(tmp_path, ignore_errors=True)


class TestWorkflowInitialize:
    """Tests for Workflow.initialize()."""

    def test_initialize_raises_if_binary_missing(self):
        """initialize() raises RuntimeError when runner binary is not on PATH."""
        workflow = get_workflow("ciaa_caseworker")
        with patch("shutil.which", return_value=None), patch(
            "os.path.isfile", return_value=False
        ):
            with pytest.raises(RuntimeError, match="not found on PATH"):
                workflow.initialize(runner="copilot")

    def test_initialize_unknown_runner_raises(self):
        """initialize() raises ValueError for unknown runner name."""
        workflow = get_workflow("ciaa_caseworker")
        with pytest.raises(ValueError, match="Unknown runner"):
            workflow.initialize(runner="unknown_runner")

    def test_initialize_kiro_symlinks_agent(self, tmp_path):
        """initialize(runner='kiro') calls _symlink_kiro_agent."""
        workflow = get_workflow("ciaa_caseworker")
        fake_agents_dir = tmp_path / ".kiro" / "agents"

        with patch("shutil.which", return_value="/usr/bin/kiro-cli"), patch(
            "pathlib.Path.home", return_value=tmp_path
        ):
            workflow.initialize(runner="kiro")

        agent_link = fake_agents_dir / "jawafdehi-caseworker.json"
        assert agent_link.is_symlink()
