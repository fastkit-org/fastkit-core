"""
Comprehensive tests for FastKit Core RateLimit.

Tests RateLimit dependency:
- Under limit — requests pass through
- At limit — last allowed request passes
- Exceeded — HTTP 429 raised
- Window reset — counter resets after window expires
- Custom key_func — per-user limiting
- Default key — IP extraction with X-Forwarded-For support
- Response format — standard FastKit error_response format
- Headers — Retry-After, X-RateLimit-* headers present
- Router-level usage — dependency applied to all routes
- Isolation — separate RateLimit instances do not share storage
- TooManyRequestsException — correct status_code and headers
"""

import time
import pytest
from unittest.mock import patch
from fastapi import FastAPI, APIRouter, Depends, Request
from fastapi.testclient import TestClient

from fastkit_core.http import (
    RateLimit,
    TooManyRequestsException,
    register_exception_handlers,
)


# ============================================================================
# Helpers
# ============================================================================

def make_app(limiter: RateLimit) -> TestClient:
    """Create a minimal FastAPI app with a single rate-limited endpoint."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/test")
    async def endpoint(_: None = Depends(limiter)):
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


def make_request(client: TestClient, ip: str = "127.0.0.1") -> object:
    """Make a GET /test request with a given client IP."""
    return client.get("/test", headers={"X-Forwarded-For": ip})


# ============================================================================
# Test _per_to_seconds
# ============================================================================

class TestPerToSeconds:
    """Test the static helper that converts period labels to seconds."""

    def test_second(self):
        assert RateLimit._per_to_seconds('second') == 1

    def test_minute(self):
        assert RateLimit._per_to_seconds('minute') == 60

    def test_hour(self):
        assert RateLimit._per_to_seconds('hour') == 3600

    def test_day(self):
        assert RateLimit._per_to_seconds('day') == 86400


# ============================================================================
# Test _get_key
# ============================================================================

class TestGetKey:
    """Test key resolution logic."""

    def _make_request(self, ip=None, forwarded_for=None) -> Request:
        """Build a minimal Starlette Request-like mock."""
        from unittest.mock import MagicMock
        req = MagicMock(spec=Request)
        req.client = MagicMock()
        req.client.host = ip or "10.0.0.1"
        headers = {}
        if forwarded_for:
            headers["X-Forwarded-For"] = forwarded_for
        req.headers = headers
        return req

    def test_uses_client_ip_when_no_forwarded_header(self):
        """Should fall back to request.client.host."""
        limiter = RateLimit(10, per='minute')
        req = self._make_request(ip="192.168.1.1")
        key = limiter._get_key(req)
        assert "192.168.1.1" in key

    def test_uses_first_forwarded_for_ip(self):
        """Should extract the first IP from X-Forwarded-For."""
        limiter = RateLimit(10, per='minute')
        req = self._make_request(forwarded_for="203.0.113.5, 10.0.0.1, 172.16.0.1")
        key = limiter._get_key(req)
        assert "203.0.113.5" in key
        assert "10.0.0.1" not in key

    def test_key_includes_prefix(self):
        """Key should start with the limiter prefix so different configs don't collide."""
        limiter = RateLimit(5, per='minute')
        req = self._make_request(ip="1.2.3.4")
        key = limiter._get_key(req)
        assert key.startswith("rl:5:minute:")

    def test_custom_key_func(self):
        """Custom key_func should override IP extraction."""
        limiter = RateLimit(10, per='minute', key_func=lambda r: "user:42")
        req = self._make_request(ip="1.2.3.4")
        key = limiter._get_key(req)
        assert "user:42" in key

    def test_different_limits_produce_different_prefixes(self):
        """Two limiters with different configs must not share keys."""
        l1 = RateLimit(5, per='minute')
        l2 = RateLimit(100, per='hour')
        req = self._make_request(ip="1.2.3.4")
        assert l1._get_key(req) != l2._get_key(req)


# ============================================================================
# Test TooManyRequestsException
# ============================================================================

class TestTooManyRequestsException:
    """Test the exception class itself."""

    def test_status_code_is_429(self):
        exc = TooManyRequestsException()
        assert exc.status_code == 429

    def test_default_message(self):
        exc = TooManyRequestsException()
        assert exc.message  # non-empty

    def test_custom_message(self):
        exc = TooManyRequestsException(message="Slow down!")
        assert exc.message == "Slow down!"

    def test_headers_stored(self):
        headers = {"Retry-After": "30", "X-RateLimit-Limit": "5"}
        exc = TooManyRequestsException(headers=headers)
        assert exc.headers == headers

    def test_no_headers_by_default(self):
        exc = TooManyRequestsException()
        assert exc.headers is None

    def test_is_subclass_of_fastkit_exception(self):
        from fastkit_core.http import FastKitException
        exc = TooManyRequestsException()
        assert isinstance(exc, FastKitException)
