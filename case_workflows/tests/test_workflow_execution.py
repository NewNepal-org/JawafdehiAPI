"""
Tests for Workflow execution methods (setup_work_dir, execute).
"""

import shutil
from unittest.mock import AsyncMock, patch

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

    def test_setup_creates_work_dir(self, tmp_path, settings):
        """setup_work_dir creates the work directory."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()

        work_dir = workflow.setup_work_dir(run)

        assert work_dir.is_dir()

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
        assert (work_dir / "logs").is_dir()

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_initialises_case_data(self, tmp_path, settings):
        """setup_work_dir initialises run.case_data with the expected schema."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()

        workflow.setup_work_dir(run)
        run.refresh_from_db()

        assert run.case_data["is_complete"] is False
        assert isinstance(run.case_data["steps"], dict)
        assert isinstance(run.case_data["files"], dict)

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
        assert (work_dir2 / "sources" / "raw").is_dir()

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_setup_preserves_existing_case_data(self, tmp_path, settings):
        """If run.case_data already has steps, it is preserved on re-setup."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()

        # Pre-populate case_data as if a step was already done
        existing_data = {
            "is_complete": False,
            "steps": {"initialize-casework": {"status": "complete"}},
            "files": {},
        }
        run.case_data = existing_data
        run.save()

        workflow.setup_work_dir(run)
        run.refresh_from_db()

        # Existing steps should still be there
        assert "initialize-casework" in run.case_data["steps"]

        shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.mark.django_db
class TestWorkflowExecute:
    """Tests for Workflow.execute() — mocks the deep agent to avoid real API calls."""

    def _make_run(self, case_id="case-testexec01"):
        return CaseWorkflowRun.objects.create(
            case_id=case_id,
            workflow_id="ciaa_caseworker",
        )

    def test_execute_skips_already_complete_run(self, tmp_path, settings):
        """execute() exits immediately if run.case_data shows is_complete=True."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()
        run.case_data = {"is_complete": True, "steps": {}, "files": {}}
        run.save()

        # Setup work dir so the directory exists
        workflow.setup_work_dir(run)
        # Manually set is_complete back (setup_work_dir preserves it)
        run.case_data = {"is_complete": True, "steps": {}, "files": {}}
        run.save()

        # Patch _execute_async with AsyncMock so asyncio.run can properly await it
        with patch.object(
            workflow, "_execute_async", new_callable=AsyncMock
        ) as mock_async:
            workflow.execute(run, model="openai:gpt-4o")
            mock_async.assert_called_once()

        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_execute_calls_asyncio_run(self, tmp_path, settings):
        """execute() delegates to asyncio.run(_execute_async(...)) with correct args."""
        settings.CASE_WORKFLOWS_WORK_DIR = str(tmp_path)
        workflow = get_workflow("ciaa_caseworker")
        run = self._make_run()
        workflow.setup_work_dir(run)

        # Patch _execute_async with AsyncMock so asyncio.run can properly await it
        with patch.object(
            workflow, "_execute_async", new_callable=AsyncMock
        ) as mock_async:
            workflow.execute(
                run, model="anthropic:claude-3-5-sonnet", api_key="test-key"
            )
            mock_async.assert_called_once_with(
                run,
                model="anthropic:claude-3-5-sonnet",
                api_key="test-key",
                base_url=None,
                verbose=False,
                recursion_limit=100,
            )
