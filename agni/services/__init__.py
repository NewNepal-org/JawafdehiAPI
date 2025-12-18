"""
AgniService implementation for document processing and entity extraction.

Provides the AgniService orchestration layer that coordinates between
GenAI services, search services, and persistence for the Jawafdehi platform.
"""

from .agni_service import AgniService, AgniServiceError, create_agni_service

__all__ = ['AgniService', 'AgniServiceError', 'create_agni_service']