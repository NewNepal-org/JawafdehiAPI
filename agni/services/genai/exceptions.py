"""Exception classes for GenAI service."""


class GenAIServiceError(Exception):
    """Base exception raised when GenAI operations fail."""
    pass


class LLMAPIError(GenAIServiceError):
    """Exception raised when LLM API fails."""
    pass


class InvalidExtractionError(GenAIServiceError):
    """Exception raised when LLM returns invalid extraction data."""
    pass


class ExtractionTimeoutError(GenAIServiceError):
    """Exception raised when extraction times out."""
    pass