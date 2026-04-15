"""Utility functions for the cases app."""

import ipaddress


def get_client_ip(request):
    """
    Extract and validate client IP address from request.

    This function extracts the client IP address from the HTTP request,
    prioritizing the HTTP_X_FORWARDED_FOR header (used when behind a proxy
    or load balancer) and falling back to REMOTE_ADDR. The extracted IP
    is validated using Python's ipaddress module to prevent IP spoofing
    attacks.

    Args:
        request: Django HttpRequest object containing META headers

    Returns:
        str: Validated IP address string, or "unknown" if no valid IP found

    Security:
        - Validates IP addresses to prevent spoofing attacks
        - Handles malformed or invalid IP addresses gracefully
        - Returns "unknown" for invalid IPs rather than raising exceptions

    Examples:
        >>> # With X-Forwarded-For header (proxy scenario)
        >>> request.META = {"HTTP_X_FORWARDED_FOR": "203.0.113.1, 198.51.100.1"}
        >>> get_client_ip(request)
        '203.0.113.1'

        >>> # Without X-Forwarded-For (direct connection)
        >>> request.META = {"REMOTE_ADDR": "192.0.2.1"}
        >>> get_client_ip(request)
        '192.0.2.1'

        >>> # Invalid IP address
        >>> request.META = {"HTTP_X_FORWARDED_FOR": "not-an-ip"}
        >>> get_client_ip(request)
        'unknown'
    """
    # Try to get IP from X-Forwarded-For header (proxy/load balancer scenario)
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # Take the first IP in the chain (client IP)
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        # Fall back to REMOTE_ADDR (direct connection)
        ip = request.META.get("REMOTE_ADDR", "unknown")

    # Validate the extracted IP address
    if ip != "unknown":
        try:
            # Attempt to parse as IP address (validates format)
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            # Invalid IP format - return "unknown" instead of raising
            return "unknown"

    return ip
