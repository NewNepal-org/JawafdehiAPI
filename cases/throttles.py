"""
Rate throttling classes for API endpoints.
"""

from rest_framework.throttling import AnonRateThrottle


class IPBasedRateThrottle(AnonRateThrottle):
    """
    IP-based rate throttle for general API endpoints.

    Limits requests per IP address to prevent abuse.
    Default: 100 requests per hour per IP.
    """

    rate = "100/hour"

    def get_cache_key(self, request, view):
        """
        Use IP address as the throttle key.
        """
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class StrictIPRateThrottle(AnonRateThrottle):
    """
    Stricter IP-based rate throttle for write operations.

    Default: 20 requests per hour per IP.
    """

    rate = "20/hour"

    def get_cache_key(self, request, view):
        """
        Use IP address as the throttle key.
        """
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class FeedbackRateThrottle(AnonRateThrottle):
    """
    Rate throttle for feedback submissions.

    Limits to 5 submissions per hour per IP address.
    """

    rate = "5/hour"

    def get_cache_key(self, request, view):
        """
        Use IP address as the throttle key.
        """
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
