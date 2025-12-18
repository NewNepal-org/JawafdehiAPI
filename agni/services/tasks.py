"""
Django Q tasks for asynchronous Agni document processing.

Thin wrappers around AgniService methods. All business logic lives in AgniService.
"""

import asyncio
import random
import logging
import time
from contextlib import contextmanager
from typing import Callable, Iterator, Optional, Tuple, TypeVar

from .agni_models import AgniExtractionSession
from ..models import StoredExtractionSession, SessionStatus, TaskStatus, TaskType
from ..utils import deserialize_session, serialize_session
from . import create_agni_service, AgniServiceError
from django_q.tasks import async_task
from django.db import transaction
from django.db.utils import DatabaseError, OperationalError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _iter_exception_chain(exc: BaseException) -> Iterator[BaseException]:
    """Yield an exception and its chained causes/contexts (best-effort)."""
    cur: Optional[BaseException] = exc
    while cur is not None:
        yield cur
        cur = cur.__cause__ or cur.__context__


def _is_sqlite_database_locked(exc: BaseException) -> bool:
    for e in _iter_exception_chain(exc):
        # SQLite raises OperationalError("database is locked")
        if isinstance(e, OperationalError) and "database is locked" in str(e).lower():
            return True
    return False


def _is_postgres_retryable_concurrency_error(exc: BaseException) -> bool:
    """
    Detect Postgres retryable concurrency errors:
    - serialization failure: SQLSTATE 40001
    - deadlock detected: SQLSTATE 40P01
    """
    for e in _iter_exception_chain(exc):
        # psycopg2 uses pgcode, psycopg3 uses sqlstate
        code = getattr(e, "pgcode", None) or getattr(e, "sqlstate", None)
        if code in {"40001", "40P01"}:
            return True
    return False


def _is_retryable_concurrency_error(exc: BaseException) -> bool:
    return _is_sqlite_database_locked(exc) or _is_postgres_retryable_concurrency_error(exc)


@contextmanager
def session_lock(
    session_id: str,
    *,
    attempts: int = 2,
    base_delay_s: float = 0.1,
    jitter_s: float = 0.05,
) -> Iterator[Callable[[Callable[[StoredExtractionSession], T]], T]]:
    """
    Retryable session lock helper.

    Usage:
        with session_lock(session_id) as run:
            run(lambda stored: ...mutate and save stored...)

    Notes:
    - The callback must be safe to re-run (idempotent) because it may execute twice.
    - Keeps lock time minimal by letting callers do expensive work outside of the lock.
    """

    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def run(fn: Callable[[StoredExtractionSession], T]) -> T:
        last_exc: Optional[BaseException] = None
        for attempt in range(attempts):
            try:
                with transaction.atomic():
                    stored = StoredExtractionSession.objects.select_for_update().get(id=session_id)
                    return fn(stored)
            except (OperationalError, DatabaseError) as e:
                last_exc = e
                if attempt >= attempts - 1 or not _is_retryable_concurrency_error(e):
                    raise
                delay = base_delay_s * (2**attempt) + random.uniform(0, jitter_s)
                logger.info(
                    "Retrying session write (attempt %s/%s) after %ss due to %s",
                    attempt + 2,
                    attempts,
                    round(delay, 3),
                    str(e),
                )
                time.sleep(delay)
        # Should be unreachable (loop returns or raises), but keeps mypy/linters happy.
        assert last_exc is not None
        raise last_exc

    yield run


def _load_session(session_id: str) -> Tuple[StoredExtractionSession, AgniExtractionSession]:
    """Load stored session and deserialize."""
    stored = StoredExtractionSession.objects.get(id=session_id)
    agni_session = deserialize_session(stored.session_data)
    return stored, agni_session


def _save_session(stored, agni_session, agni_service, **extra_fields):
    """Serialize and save session with progress info."""
    stored.session_data = serialize_session(agni_session)
    stored.progress_info = agni_service.get_progress_info(agni_session)
    update_fields = ['session_data', 'progress_info', 'updated_at']
    for field, value in extra_fields.items():
        setattr(stored, field, value)
        update_fields.append(field)
    stored.save(update_fields=update_fields)


def _handle_error(session_id: str, error: Exception, operation: str):
    """Log error and mark session as failed."""
    logger.error(f"{operation} failed for session {session_id}: {error}", exc_info=True)
    try:
        stored = StoredExtractionSession.objects.get(id=session_id)
        stored.mark_failed(f"{operation} failed: {error}")
    except Exception:
        logger.error(f"Failed to mark session {session_id} as failed", exc_info=True)


def ai_background_research_task(session_id: str) -> None:
    """
    Run AI background research (metadata + entity extraction).
    
    After completion, entities are available for per-entity resolution
    via ai_resolve_entity_task.
    """
    try:
        stored, agni_session = _load_session(session_id)
        stored.status = SessionStatus.PROCESSING_METADATA
        stored.save(update_fields=['status', 'updated_at'])

        agni_service = create_agni_service()
        agni_session = asyncio.run(agni_service.ai_background_research(agni_session))

        _save_session(
            stored, agni_session, agni_service,
            status=SessionStatus.PROCESSING_ENTITIES
        )

        for entity in agni_session.entities:
            task_id = async_task(
                "agni.services.tasks.ai_resolve_entity_task",
                session_id=session_id,
                entity_id=entity.entity_id,
            )

            stored.add_active_task(
                TaskType.UPDATE_ENTITY, task_id, entity_id=entity.entity_id
            )

    except StoredExtractionSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        raise
    except Exception as e:
        _handle_error(session_id, e, "Background research")
        raise


def ai_resolve_entity_task(session_id: str, entity_id: str):
    """Resolve a single entity to NES matches and return the resolved entity."""    
    try:
        # Load session and perform AI resolution
        stored, agni_session = _load_session(session_id)
        
        agni_service = create_agni_service()
        # ai_resolve_entity now returns just the modified entity, not the full session
        resolved_entity = asyncio.run(
            agni_service.ai_resolve_entity(agni_session, entity_id)
        )

        def _apply_session_update(locked_stored: StoredExtractionSession) -> None:
            # Deserialize current session data
            current_agni_session = deserialize_session(locked_stored.session_data)

            # Update the specific entity in the session
            for i, entity in enumerate(current_agni_session.entities):
                if entity.entity_id == entity_id:
                    current_agni_session.entities[i] = resolved_entity
                    break
            else:
                raise ValueError(f"Entity not found in session: {entity_id}")

            # Mark this task as completed (do NOT remove it from task list)
            # so the UI/audit trail can show that entity resolution finished.
            updated_tasks = locked_stored.tasks or []  # StoredExtractionSession JSON task list
            for task in updated_tasks:
                if (
                    task.get("task_type") == TaskType.UPDATE_ENTITY.value
                    and str(task.get("entity_id")) == str(entity_id)
                ):
                    task["status"] = TaskStatus.COMPLETED
                    break
            locked_stored.tasks = updated_tasks

            # Check if all entity resolution tasks are complete
            remaining_entity_tasks = [
                task
                for task in locked_stored.get_active_tasks()
                if (
                    task.task_type == TaskType.UPDATE_ENTITY.value
                    and task.status in (TaskStatus.QUEUED, TaskStatus.RUNNING)
                )
            ]

            # If no more entity resolution tasks, move to awaiting review
            if (
                not remaining_entity_tasks
                and locked_stored.status == SessionStatus.PROCESSING_ENTITIES
            ):
                locked_stored.status = SessionStatus.AWAITING_REVIEW
                logger.info(
                    "Session %s moved to AWAITING_REVIEW - all entity resolution tasks completed",
                    session_id,
                )

            # Save updated session
            locked_stored.session_data = serialize_session(current_agni_session)
            locked_stored.progress_info = agni_service.get_progress_info(current_agni_session)
            locked_stored.save(
                update_fields=['session_data', 'progress_info', 'tasks', 'status', 'updated_at']
            )

        with session_lock(session_id, attempts=2) as run:
            run(_apply_session_update)

        return resolved_entity

    except StoredExtractionSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        raise
    except ValueError as e:
        logger.error(f"Entity not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Entity resolution failed for {entity_id}: {e}", exc_info=True)
        raise


def update_entity_task(session_id: str, entity_index: int, message: str) -> None:
    """Update a specific entity based on user conversation."""
    try:
        stored, agni_session = _load_session(session_id)

        agni_service = create_agni_service()
        agni_service.validate_entity_index(agni_session, entity_index)
        agni_session = asyncio.run(
            agni_service.update_entity(agni_session, entity_index, message)
        )

        _save_session(stored, agni_session, agni_service)

    except StoredExtractionSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        raise
    except Exception as e:
        logger.error(f"Entity update failed for index {entity_index}: {e}", exc_info=True)
        raise


def persist_changes_task(session_id: str, description: str, author_id: str) -> None:
    """Persist approved entity changes to NES."""
    try:
        stored, agni_session = _load_session(session_id)

        agni_service = create_agni_service()
        agni_service.validate_all_entities_resolved(agni_session)
        agni_service.persist(agni_session, description, author_id)

        stored.mark_completed()

    except StoredExtractionSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        raise
    except Exception as e:
        _handle_error(session_id, e, "Persistence")
        raise
