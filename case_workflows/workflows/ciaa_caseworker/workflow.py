"""
CIAA Caseworker workflow — processes Special Court cases from the NGM
database and creates Jawafdehi accountability cases.

Template location: ``case_workflows/workflows/ciaa_caseworker/``
Original source:   ``.agents/caseworker/``
"""

from __future__ import annotations

import logging
import os
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

    Steps (which become ``prd.json`` user stories at runtime):

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
        Return Jawafdehi Case ``case_id`` values eligible for this workflow.

        A case is eligible if:
        - It is a CORRUPTION case in DRAFT or IN_REVIEW state
          (CLOSED and PUBLISHED cases are intentionally excluded)
        - Its title contains one of the known CIAA Special Court case numbers,
          preventing unrelated CORRUPTION drafts from being picked up
        - There is no existing completed CaseWorkflowRun for it

        Returns a list of Jawafdehi ``Case.case_id`` strings
        (e.g. ``["case-abc123", "case-def456"]``).
        """
        from case_workflows.models import CaseWorkflowRun
        from cases.models import Case, CaseState, CaseType

        from case_workflows.workflows.ciaa_caseworker.constants import CIAA_CASE_NUMBERS

        # Find already-completed case IDs for this workflow
        completed_case_ids = set(
            CaseWorkflowRun.objects.filter(
                workflow_id=self.workflow_id,
                is_complete=True,
            ).values_list("case_id", flat=True)
        )

        # DRAFT and IN_REVIEW only — CLOSED and PUBLISHED are excluded by design
        rows = (
            Case.objects.filter(
                case_type=CaseType.CORRUPTION,
                state__in=[CaseState.DRAFT, CaseState.IN_REVIEW],
            )
            .exclude(case_id__in=completed_case_ids)
            .values_list("case_id", "title")
        )

        # Post-filter: only cases whose title contains a known CIAA case number.
        # Avoids picking up unrelated CORRUPTION drafts that would fail at US-001.
        return [
            case_id
            for case_id, title in rows
            if any(num in title for num in CIAA_CASE_NUMBERS)
        ]

    def get_template_dir(self) -> Path:
        return TEMPLATE_DIR

    def get_agent_name(self) -> str:
        return "jawafdehi-caseworker"

    def get_mcp_config_path(self) -> Path | None:
        candidate = TEMPLATE_DIR / "etc" / "copilot-mcp-config.json"
        return candidate if candidate.exists() else None

    def on_initialize(self, runner: str) -> None:
        """
        Provider-specific setup:

        **kiro**: symlink the agent JSON into ``~/.kiro/agents/`` so kiro
        can discover the ``jawafdehi-caseworker`` agent.
        """
        if runner == "kiro":
            self._symlink_kiro_agent()

    def _symlink_kiro_agent(self) -> None:
        """Symlink the agent definition into ~/.kiro/agents/."""
        agent_src = TEMPLATE_DIR / "agents" / "jawafdehi-caseworker.json"
        agents_dir = Path.home() / ".kiro" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        agent_dest = agents_dir / "jawafdehi-caseworker.json"

        if agent_dest.is_symlink():
            if agent_dest.resolve() == agent_src.resolve():
                logger.debug("kiro agent symlink already correct: %s", agent_dest)
                return
            logger.warning("Removing stale kiro agent symlink: %s", agent_dest)
            agent_dest.unlink()
        elif agent_dest.exists():
            logger.warning(
                "kiro agent file already exists (not a symlink) — leaving in place: %s",
                agent_dest,
            )
            return

        os.symlink(agent_src, agent_dest)
        logger.info("Symlinked kiro agent: %s → %s", agent_dest, agent_src)

    def on_work_dir_created(self, case_dir: Path) -> None:
        """
        CIAA-specific work directory setup:

        - ``sources/raw/``      — downloaded raw files (PDFs, HTML, etc.)
        - ``sources/markdown/`` — converted markdown versions
        """
        (case_dir / "sources" / "raw").mkdir(parents=True, exist_ok=True)
        (case_dir / "sources" / "markdown").mkdir(parents=True, exist_ok=True)
