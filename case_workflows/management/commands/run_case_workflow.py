"""
Management command to run case workflows.

Usage::

    # List all registered workflows
    python manage.py run_case_workflow --list

    # Run workflow for all eligible cases
    python manage.py run_case_workflow ciaa_caseworker

    # Run workflow for a specific case
    python manage.py run_case_workflow ciaa_caseworker --case-id case-abc123
"""

from django.core.management.base import BaseCommand, CommandError

from case_workflows.models import CaseWorkflowRun
from case_workflows.registry import get_workflow, list_workflows


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
            help="Target a specific Jawafdehi case_id instead of auto-selecting",
        )
        parser.add_argument(
            "--runner",
            type=str,
            choices=["copilot", "kiro"],
            default="copilot",
            help="Agent CLI runner to use (default: copilot)",
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

        # ---- Require workflow_id for execution ----
        workflow_id = options["workflow_id"]
        if not workflow_id:
            raise CommandError(
                "Provide a workflow_id, or use --list to see available workflows."
            )

        try:
            workflow = get_workflow(workflow_id)
        except KeyError as exc:
            raise CommandError(str(exc))

        runner_name = options["runner"]
        self.stderr.write(f"Workflow: {workflow.display_name} ({workflow_id})")
        self.stderr.write(f"Runner:   {runner_name}")

        # ---- Initialize runner (validates binary + provider-specific setup) ----
        try:
            workflow.initialize(runner=runner_name)
        except (RuntimeError, ValueError) as exc:
            raise CommandError(f"Initialization failed: {exc}")

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

        # ---- Execute workflow for each case ----
        success_count = 0
        skip_count = 0
        fail_count = 0

        for cid in case_ids:
            self.stderr.write(f"\n{'=' * 60}")
            self.stderr.write(f"Processing case: {cid}")
            self.stderr.write(f"{'=' * 60}")

            run, created = CaseWorkflowRun.objects.get_or_create(
                case_id=cid,
                workflow_id=workflow_id,
            )

            if not created and run.is_complete:
                self.stderr.write("  ⏭ Skipping — already complete")
                skip_count += 1
                continue

            self.stderr.write("  ✦ Created new run" if created else "  ♻ Resuming existing run")

            try:
                workflow.setup_work_dir(run)
                self.stderr.write(f"  📁 Work dir: {run.work_dir}")
                workflow.execute(run, runner=runner_name)
            except Exception as exc:
                self.stderr.write(f"  ✗ Error: {exc}")
                fail_count += 1
                continue

            run.refresh_from_db()
            if run.is_complete:
                self.stderr.write("  ✓ Completed")
                success_count += 1
            elif run.has_failed:
                self.stderr.write(f"  ✗ Failed: {run.error_message}")
                fail_count += 1
            else:
                self.stderr.write("  … Status unclear")

        # ---- Summary ----
        self.stderr.write(f"\n{'=' * 60}")
        self.stderr.write("Summary:")
        self.stderr.write(f"  Processed: {len(case_ids)}")
        self.stderr.write(f"  Succeeded: {success_count}")
        self.stderr.write(f"  Skipped:   {skip_count}")
        self.stderr.write(f"  Failed:    {fail_count}")
