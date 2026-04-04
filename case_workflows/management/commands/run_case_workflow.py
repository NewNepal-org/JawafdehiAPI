"""
Management command to run case workflows.

Usage::

    # List all registered workflows
    python manage.py run_case_workflow --list

    # Dry-run: show eligible cases without executing
    python manage.py run_case_workflow ciaa_caseworker --dry-run

    # Run workflow for all eligible cases
    python manage.py run_case_workflow ciaa_caseworker

    # Run workflow for a specific case
    python manage.py run_case_workflow ciaa_caseworker --case-id 081-CR-0123

    # Re-run a previously completed/failed workflow
    python manage.py run_case_workflow ciaa_caseworker --case-id 081-CR-0123 --overwrite
"""

from django.core.management.base import BaseCommand, CommandError

from case_workflows.models import CaseWorkflowRun
from case_workflows.registry import get_workflow, list_workflows
from case_workflows.runner import WorkflowRunner


class Command(BaseCommand):
    help = "Run a registered case workflow against eligible cases"

    def add_arguments(self, parser):
        parser.add_argument(
            "workflow_id",
            nargs="?",
            type=str,
            help="Workflow template ID to run (e.g. ciaa_caseworker)",
        )
        parser.add_argument(
            "--case-id",
            type=str,
            help="Target a specific case instead of auto-selecting eligible ones",
        )
        parser.add_argument(
            "--max-iterations",
            type=int,
            default=15,
            help="Maximum agent loop iterations per case (default: 15)",
        )
        parser.add_argument(
            "--runner",
            type=str,
            choices=["copilot", "kiro"],
            default="copilot",
            help="Agent CLI runner to use (default: copilot)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List eligible cases and exit without executing",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Re-run even if a CaseWorkflowRun already exists (resets state)",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            dest="list_workflows",
            help="List all registered workflows and exit",
        )

    def handle(self, *args, **options):
        # ---- List workflows mode ----
        if options["list_workflows"]:
            wids = list_workflows()
            if not wids:
                self.stderr.write("No workflows registered.")
                return
            self.stderr.write("Registered workflows:")
            for wid in wids:
                wf = get_workflow(wid)
                self.stderr.write(f"  • {wid} — {wf.display_name}")
            return

        # ---- Require workflow_id for all other modes ----
        workflow_id = options["workflow_id"]
        if not workflow_id:
            raise CommandError(
                "Provide a workflow_id, or use --list to see available workflows."
            )

        try:
            workflow = get_workflow(workflow_id)
        except KeyError as exc:
            raise CommandError(str(exc))

        self.stderr.write(f"Workflow: {workflow.display_name} ({workflow_id})")

        # ---- Determine target cases ----
        specific_case = options["case_id"]
        if specific_case:
            case_ids = [specific_case]
            self.stderr.write(f"Targeting specific case: {specific_case}")
        else:
            case_ids = workflow.get_eligible_cases()
            self.stderr.write(f"Found {len(case_ids)} eligible case(s)")

        if not case_ids:
            self.stderr.write("No cases to process. Exiting.")
            return

        # ---- Dry-run mode ----
        if options["dry_run"]:
            self.stderr.write("Dry-run — eligible cases:")
            for cid in case_ids:
                existing = CaseWorkflowRun.objects.filter(
                    case_id=cid, workflow_template_id=workflow_id
                ).first()
                status = ""
                if existing:
                    if existing.is_complete:
                        status = " [COMPLETE]"
                    elif existing.has_failed:
                        status = " [FAILED]"
                    else:
                        status = " [IN PROGRESS]"
                self.stderr.write(f"  • {cid}{status}")
            return

        # ---- Execute workflow for each case ----
        overwrite = options["overwrite"]
        max_iterations = options["max_iterations"]
        runner_name = options["runner"]

        success_count = 0
        skip_count = 0
        fail_count = 0

        for cid in case_ids:
            self.stderr.write(f"\n{'=' * 60}")
            self.stderr.write(f"Processing case: {cid}")
            self.stderr.write(f"{'=' * 60}")

            # Get or create the run record
            run, created = CaseWorkflowRun.objects.get_or_create(
                case_id=cid,
                workflow_template_id=workflow_id,
            )

            if not created:
                if run.is_complete and not overwrite:
                    self.stderr.write(f"  ⏭ Skipping — already complete")
                    skip_count += 1
                    continue
                if overwrite:
                    self.stderr.write(f"  ♻ Resetting existing run")
                    run.is_complete = False
                    run.has_failed = False
                    run.error_message = ""
                    run.started_at = None
                    run.completed_at = None
                    run.case_data = {}
                    run.save()
            else:
                self.stderr.write(f"  ✦ Created new CaseWorkflowRun")

            # Set up working directory and execute
            wf_runner = WorkflowRunner(workflow, run)

            try:
                wf_runner.setup_work_dir(overwrite=overwrite)
                self.stderr.write(f"  📁 Work dir: {run.work_dir}")

                wf_runner.execute(
                    max_iterations=max_iterations,
                    runner=runner_name,
                )
            except Exception as exc:
                self.stderr.write(f"  ✗ Error: {exc}")
                fail_count += 1
                continue

            # Report outcome
            run.refresh_from_db()
            if run.is_complete:
                self.stderr.write(f"  ✓ Completed")
                success_count += 1
            elif run.has_failed:
                self.stderr.write(f"  ✗ Failed: {run.error_message}")
                fail_count += 1
            else:
                self.stderr.write(f"  … Status unclear")

        # ---- Summary ----
        self.stderr.write(f"\n{'=' * 60}")
        self.stderr.write("Summary:")
        self.stderr.write(f"  Processed: {len(case_ids)}")
        self.stderr.write(f"  Succeeded: {success_count}")
        self.stderr.write(f"  Skipped:   {skip_count}")
        self.stderr.write(f"  Failed:    {fail_count}")
