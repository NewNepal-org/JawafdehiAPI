"""Tests for cases.utils module."""

import pytest
from django.test import RequestFactory

from cases.utils import get_client_ip


class TestGetClientIP:
    """Test suite for get_client_ip() utility function."""

    @pytest.fixture
    def request_factory(self):
        """Provide a Django RequestFactory for creating test requests."""
        return RequestFactory()

    def test_extracts_ip_from_x_forwarded_for_single_ip(self, request_factory):
        """Test extraction from X-Forwarded-For with single IP."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1"

        result = get_client_ip(request)

        assert result == "203.0.113.1"

    def test_extracts_first_ip_from_x_forwarded_for_chain(self, request_factory):
        """Test extraction from X-Forwarded-For with multiple IPs (takes first)."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 198.51.100.1, 192.0.2.1"

        result = get_client_ip(request)

        assert result == "203.0.113.1"

    def test_strips_whitespace_from_x_forwarded_for(self, request_factory):
        """Test that whitespace is stripped from extracted IP."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "  203.0.113.1  , 198.51.100.1"

        result = get_client_ip(request)

        assert result == "203.0.113.1"

    def test_falls_back_to_remote_addr(self, request_factory):
        """Test fallback to REMOTE_ADDR when X-Forwarded-For is absent."""
        request = request_factory.get("/")
        request.META["REMOTE_ADDR"] = "192.0.2.1"

        result = get_client_ip(request)

        assert result == "192.0.2.1"

    def test_returns_unknown_when_no_ip_available(self, request_factory):
        """Test returns 'unknown' when neither header is present."""
        request = request_factory.get("/")
        # Remove the default REMOTE_ADDR set by RequestFactory
        del request.META["REMOTE_ADDR"]

        result = get_client_ip(request)

        assert result == "unknown"

    def test_validates_ipv4_address(self, request_factory):
        """Test that valid IPv4 addresses are accepted."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.1"

        result = get_client_ip(request)

        assert result == "192.168.1.1"

    def test_validates_ipv6_address(self, request_factory):
        """Test that valid IPv6 addresses are accepted."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

        result = get_client_ip(request)

        assert result == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

    def test_rejects_invalid_ip_format(self, request_factory):
        """Test that invalid IP format returns 'unknown'."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "not-an-ip-address"

        result = get_client_ip(request)

        assert result == "unknown"

    def test_rejects_malformed_ip(self, request_factory):
        """Test that malformed IP returns 'unknown'."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "999.999.999.999"

        result = get_client_ip(request)

        assert result == "unknown"

    def test_rejects_empty_string(self, request_factory):
        """Test that empty string returns 'unknown'."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = ""
        request.META["REMOTE_ADDR"] = "192.0.2.1"

        result = get_client_ip(request)

        # Should fall back to REMOTE_ADDR when X-Forwarded-For is empty
        assert result == "192.0.2.1"

    def test_handles_sql_injection_attempt(self, request_factory):
        """Test that SQL injection attempts in IP field are rejected."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "'; DROP TABLE users; --"

        result = get_client_ip(request)

        assert result == "unknown"

    def test_handles_xss_attempt(self, request_factory):
        """Test that XSS attempts in IP field are rejected."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "<script>alert('xss')</script>"

        result = get_client_ip(request)

        assert result == "unknown"

    def test_prioritizes_x_forwarded_for_over_remote_addr(self, request_factory):
        """Test that X-Forwarded-For takes precedence over REMOTE_ADDR."""
        request = request_factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1"
        request.META["REMOTE_ADDR"] = "192.0.2.1"

        result = get_client_ip(request)

        assert result == "203.0.113.1"

    def test_validates_remote_addr_when_used(self, request_factory):
        """Test that REMOTE_ADDR is also validated."""
        request = request_factory.get("/")
        request.META["REMOTE_ADDR"] = "invalid-ip"

        result = get_client_ip(request)

        assert result == "unknown"
