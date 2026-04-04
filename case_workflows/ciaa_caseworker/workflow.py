"""
CIAA Caseworker workflow — processes Special Court cases from the NGM
database and creates Jawafdehi accountability cases.

This is the original caseworker workflow migrated from
``.agents/caseworker/`` into the Django ``case_workflows`` framework.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from case_workflows.registry import register
from case_workflows.workflow import Workflow, WorkflowStep

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent


@register
class CIAACaseworkerWorkflow(Workflow):
    """
    Workflow for processing CIAA Special Court corruption cases.

    Steps mirror the user stories in ``prd-template.json``:

    1. Initialize casework folder & verify eligibility
    2. Fetch judicial data (NGM extract, CIAA press release, charge sheet, bolpatra)
    3. Fetch news articles via web search
    4. Convert remaining documents to markdown
    5. Draft the case locally
    6. Submit the case to Jawafdehi
    """

    @property
    def workflow_id(self) -> str:
        return "ciaa_caseworker"

    @property
    def display_name(self) -> str:
        return "CIAA Caseworker"

    @property
    def steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                id="US-001",
                title="Initialize Casework",
                description=(
                    "Verifies case is eligible for processing, and setup "
                    "the necessary casework directories"
                ),
                priority=1,
                acceptance_criteria=[
                    "Verify the case exists in ngm database",
                    "Required folders are there and are empty",
                    "progress.log has marked the workflow is eligible for running",
                ],
            ),
            WorkflowStep(
                id="US-002",
                title="Fetch Judicial Data",
                description="Pull the crucial sources and factual data to start the case work.",
                priority=2,
                acceptance_criteria=[
                    "sources/case_<case_number>_<date-time>.md file exists",
                    "CIAA Press release raw file is downloaded",
                    "CIAA Press release converted to markdown",
                    "AG charge sheet raw file is downloaded",
                    "AG charge sheet converted to markdown",
                    "Bolpatra downloaded if IFB/RFP/EOI/PQ numbers found",
                ],
            ),
            WorkflowStep(
                id="US-003",
                title="Fetch News Articles",
                description="Fetch news items from Web search regarding the case.",
                priority=3,
                acceptance_criteria=[
                    "Web search executed",
                    "Relevant news items fetched",
                    "News articles saved as markdown",
                ],
            ),
            WorkflowStep(
                id="US-004",
                title="Convert Remaining Documents to Markdown",
                description="Convert remaining raw files to markdown.",
                priority=4,
                acceptance_criteria=[
                    "All remaining raw files converted to markdown",
                ],
            ),
            WorkflowStep(
                id="US-005",
                title="Draft a Case Locally",
                description=(
                    "Prepare the information necessary to file a Jawafdehi case."
                ),
                priority=5,
                acceptance_criteria=[
                    "A local case draft file exists",
                    "Case draft has all information to submit to Jawafdehi",
                    "Case draft has gone through AI review",
                ],
            ),
            WorkflowStep(
                id="US-006",
                title="Submit the case to Jawafdehi",
                description="Submit the case to the Jawafdehi website.",
                priority=6,
                acceptance_criteria=[
                    "Jawafdehi case is drafted",
                    "All fields populated",
                    "Case review passes",
                ],
            ),
        ]

    def get_eligible_cases(self) -> List[str]:
        """
        Return Special Court case numbers that are eligible for processing.

        A case is eligible if:
        - It exists in the NGM database as a Special Court case
        - There is no existing completed CaseWorkflowRun for it

        NOTE: This is a placeholder that returns an empty list.
        In production, this should query the NGM database for recent
        Special Court cases and filter out already-processed ones.
        """
        from case_workflows.models import CaseWorkflowRun

        # Find already-completed case IDs for this workflow
        completed_case_ids = set(
            CaseWorkflowRun.objects.filter(
                workflow_template_id=self.workflow_id,
                is_complete=True,
            ).values_list("case_id", flat=True)
        )

        # TODO: Query NGM database for eligible Special Court cases.
        # For now, return empty — users should use --case-id to specify
        # individual cases until the NGM query is implemented.
        #
        # Example future implementation:
        #   from ngm.models import CourtCase  # or NGM SQL query
        #   ngm_cases = CourtCase.objects.using("ngm").filter(
        #       court_identifier="special",
        #       registration_date_ad__gte=cutoff_date,
        #   ).values_list("case_number", flat=True)
        #   return [c for c in ngm_cases if c not in completed_case_ids]

        logger.info(
            "get_eligible_cases() not yet connected to NGM. "
            "Use --case-id to specify cases manually."
        )
        return []

    def get_prd_template(self) -> dict:
        """Load prd-template.json from the template directory."""
        prd_path = TEMPLATE_DIR / "etc" / "prd-template.json"
        with open(prd_path) as f:
            return json.load(f)

    def get_instructions_dir(self) -> Path:
        """Return the instructions directory path."""
        return TEMPLATE_DIR / "instructions"

    def get_agent_name(self) -> str:
        return "jawafdehi-caseworker"

    def get_mcp_config_path(self) -> Path | None:
        candidate = TEMPLATE_DIR / "etc" / "copilot-mcp-config.json"
        return candidate if candidate.exists() else None
