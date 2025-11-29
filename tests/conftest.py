"""
Pytest configuration for test suite.

Ensures environment variables are set to their default values during testing.
"""

import pytest
from django.conf import settings


@pytest.fixture(autouse=True)
def reset_feature_flags(settings):
    """
    Reset all feature flags to their default values for each test.
    
    This ensures tests run with predictable, default behavior unless
    explicitly overridden within a specific test.
    """
    # Reset EXPOSE_CASES_IN_REVIEW to default (False)
    settings.EXPOSE_CASES_IN_REVIEW = False
