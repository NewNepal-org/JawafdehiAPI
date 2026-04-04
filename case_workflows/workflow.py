"""
Abstract base class for case workflows.

Each workflow template (e.g. ciaa_caseworker) provides a concrete subclass
that defines the steps, case-selection criteria, and file locations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class WorkflowStep:
    """Represents one step / user-story in a workflow PRD."""

    id: str
    title: str
    description: str
    priority: int
    acceptance_criteria: List[str] = field(default_factory=list)


class Workflow(ABC):
    """
    Abstract base class for case workflows.

    Concrete implementations live in ``case_workflows/<template_id>/workflow.py``
    and are registered via the ``@register`` decorator from ``registry.py``.
    """

    # ------------------------------------------------------------------
    # Required properties
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def workflow_id(self) -> str:
        """
        Unique identifier for this workflow template.

        Convention: lowercase, underscores (e.g. ``ciaa_caseworker``).
        Must match the directory name under ``case_workflows/``.
        """
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in logs / admin."""
        ...

    @property
    @abstractmethod
    def steps(self) -> List[WorkflowStep]:
        """Ordered list of workflow steps."""
        ...

    # ------------------------------------------------------------------
    # Required methods
    # ------------------------------------------------------------------

    @abstractmethod
    def get_eligible_cases(self) -> List[str]:
        """
        Return a list of case identifiers eligible for this workflow.

        The identifiers are opaque strings — could be NGM case numbers,
        Jawafdehi case IDs, or any external reference depending on the
        workflow template.

        The management command will iterate over these and create / resume
        a ``CaseWorkflowRun`` for each.
        """
        ...

    @abstractmethod
    def get_prd_template(self) -> dict:
        """Return the parsed PRD template dict for this workflow."""
        ...

    @abstractmethod
    def get_instructions_dir(self) -> Path:
        """Return absolute path to the instructions directory for this template."""
        ...

    # ------------------------------------------------------------------
    # Optional overrides
    # ------------------------------------------------------------------

    def get_template_dir(self) -> Path:
        """
        Return the root directory of this workflow template package.

        Default implementation infers it from the module's ``__file__``.
        """
        import inspect

        cls_file = inspect.getfile(type(self))
        return Path(cls_file).resolve().parent

    def get_agent_name(self) -> str:
        """Agent name passed to the CLI runner (e.g. ``jawafdehi-caseworker``)."""
        return "jawafdehi-caseworker"

    def get_mcp_config_path(self) -> Path | None:
        """
        Return path to an MCP config JSON file, or ``None`` to skip.

        Looked up relative to the template directory by default.
        """
        candidate = self.get_template_dir() / "etc" / "copilot-mcp-config.json"
        return candidate if candidate.exists() else None
