"""
Tests for the WorkflowRunner.
"""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from case_workflows.models import CaseWorkflowRun
from case_workflows.registry import get_workflow
from case_workflows.runner import WorkflowRunner


@pytest.mark.django_db
class TestWorkflowRunnerSetup:
    """Tests for WorkflowRunner.setup_work_dir()."""

    def _make_runner(self, case_id="081-CR-TEST"):
        workflow = get_workflow("ciaa_caseworker")
        run = CaseWorkflowRun.objects.create(
            case_id=case_id,
            workflow_template_id="ciaa_caseworker",
        )
        return WorkflowRunner(workflow, run), run

    def test_setup_creates_directory_structure(self, tmp_path, settings):
        """setup_work_dir creates the expected directory tree."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        runner, run = self._make_runner()

        work_dir = runner.setup_work_dir()

        assert work_dir.is_dir()
        assert (work_dir / "sources" / "raw").is_dir()
        assert (work_dir / "sources" / "markdown").is_dir()
        assert (work_dir / "prd.json").is_file()
        assert (work_dir / "instructions").exists()
        assert (work_dir / "progress.log").is_file()

        # Model should be updated with work_dir
        run.refresh_from_db()
        assert run.work_dir == str(work_dir)

        # Clean up
        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_prd_is_valid_json(self, tmp_path, settings):
        """The prd.json in the work dir should be valid JSON."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        runner, _ = self._make_runner()

        work_dir = runner.setup_work_dir()
        with open(work_dir / "prd.json") as f:
            prd = json.load(f)

        assert prd["project"] == "Jawafdehi"
        assert prd["is_complete"] is False

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_work_dir_path_structure(self, tmp_path, settings):
        """Work dir follows <base>/workflows/<workflow_id>/<case_id>/ pattern."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        runner, _ = self._make_runner(case_id="081-CR-0099")

        work_dir = runner.setup_work_dir()

        assert work_dir == tmp_path / "ciaa_caseworker" / "081-CR-0099"

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_reuses_existing_dir(self, tmp_path, settings):
        """If dir exists and overwrite=False, it reuses the directory."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        runner, _ = self._make_runner()

        work_dir1 = runner.setup_work_dir()
        marker = work_dir1 / "marker.txt"
        marker.write_text("hello")

        work_dir2 = runner.setup_work_dir(overwrite=False)
        assert work_dir1 == work_dir2
        assert marker.exists()

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_overwrite_recreates_dir(self, tmp_path, settings):
        """overwrite=True removes old dir and creates fresh one."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        runner, _ = self._make_runner()

        work_dir1 = runner.setup_work_dir()
        marker = work_dir1 / "marker.txt"
        marker.write_text("hello")

        work_dir2 = runner.setup_work_dir(overwrite=True)
        assert work_dir1 == work_dir2
        assert not marker.exists()  # old marker removed
        assert (work_dir2 / "prd.json").exists()  # fresh PRD

        shutil.rmtree(tmp_path, ignore_errors=True)
