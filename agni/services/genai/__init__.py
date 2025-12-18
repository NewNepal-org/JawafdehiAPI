"""
GenAI package for AI-powered document processing and entity extraction.

Provides functionality for extracting metadata and entities from documents
using AI/ML models, with support for Nepali language content.
"""

from .exceptions import GenAIServiceError, LLMAPIError, InvalidExtractionError, ExtractionTimeoutError
from .service import GenAIService, create_genai_service

__all__ = [
    "Extraction",
    "GenAIService", 
    "create_genai_service",
    "GenAIServiceError",
    "LLMAPIError", 
    "InvalidExtractionError",
    "ExtractionTimeoutError",
]