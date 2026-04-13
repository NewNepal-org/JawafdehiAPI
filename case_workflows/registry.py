"""
Workflow registry — discovers and stores concrete ``Workflow`` subclasses.

Workflow templates register themselves with the ``@register`` decorator::

    from case_workflows.registry import register
    from case_workflows.workflow import Workflow

    @register
    class MyCaseWorkflow(Workflow):
        ...

The registry is populated on Django startup via ``CaseWorkflowsConfig.ready()``.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from case_workflows.workflow import Workflow

logger = logging.getLogger(__name__)

_registry: dict[str, Workflow] = {}


def register(workflow_cls):
    """
    Class decorator that instantiates and registers a Workflow subclass.

    Usage::

        @register
        class CIAACaseworker(Workflow):
            ...
    """
    instance = workflow_cls()
    wid = instance.workflow_id
    if wid in _registry:
        logger.warning(
            "Overwriting workflow '%s' (was %s, now %s)",
            wid,
            type(_registry[wid]).__name__,
            workflow_cls.__name__,
        )
    _registry[wid] = instance
    logger.debug("Registered workflow: %s", wid)
    return workflow_cls


def get_workflow(workflow_id: str) -> Workflow:
    """
    Look up a registered workflow by its template ID.

    Raises ``KeyError`` if not found.
    """
    try:
        return _registry[workflow_id]
    except KeyError:
        available = ", ".join(sorted(_registry.keys())) or "(none)"
        raise KeyError(
            f"Unknown workflow '{workflow_id}'. Registered workflows: {available}"
        )


def list_workflows() -> list[str]:
    """Return sorted list of registered workflow IDs."""
    return sorted(_registry.keys())


def autodiscover():
    """
    Import all ``case_workflows.workflows.<template>.workflow`` modules so
    their ``@register`` decorators fire.

    Templates live under ``case_workflows/workflows/<template_id>/workflow.py``.
    Called automatically from ``CaseWorkflowsConfig.ready()``.
    """
    import case_workflows.workflows as workflows_pkg

    for importer, modname, ispkg in pkgutil.iter_modules(workflows_pkg.__path__):
        if not ispkg:
            continue
        module_name = f"case_workflows.workflows.{modname}.workflow"
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            # Only skip when the workflow module itself is missing.
            # If a dependency import inside that module is missing, surface it.
            if exc.name == module_name:
                continue
            raise
        except Exception:
            logger.exception("Failed to import workflow module: %s", module_name)
