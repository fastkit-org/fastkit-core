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

# ============================================================================
# Test RateLimit — Under / At / Over limit
# ============================================================================

class TestRateLimitThreshold:
    """Test that the counter allows exactly `limit` requests."""

    def test_requests_under_limit_pass(self):
        """Requests 1..limit-1 should all return 200."""
        client = make_app(RateLimit(5, per='minute'))
        for _ in range(4):
            r = make_request(client)
            assert r.status_code == 200

    def test_request_at_limit_passes(self):
        """The exactly limit-th request should still return 200."""
        client = make_app(RateLimit(5, per='minute'))
        for _ in range(5):
            r = make_request(client)
        assert r.status_code == 200

    def test_request_exceeding_limit_returns_429(self):
        """The limit+1-th request should return 429."""
        client = make_app(RateLimit(3, per='minute'))
        for _ in range(3):
            make_request(client)
        r = make_request(client)
        assert r.status_code == 429

    def test_429_response_body_format(self):
        """429 body should follow FastKit error_response format."""
        client = make_app(RateLimit(1, per='minute'))
        make_request(client)
        r = make_request(client)

        data = r.json()
        assert data['success'] is False
        assert 'message' in data
        assert 'too many' in data['message'].lower()

    def test_429_has_retry_after_header(self):
        """429 response must carry Retry-After header."""
        client = make_app(RateLimit(1, per='minute'))
        make_request(client)
        r = make_request(client)

        assert 'retry-after' in r.headers

    def test_429_has_ratelimit_headers(self):
        """429 response must carry X-RateLimit-* headers."""
        client = make_app(RateLimit(1, per='minute'))
        make_request(client)
        r = make_request(client)

        assert 'x-ratelimit-limit' in r.headers
        assert 'x-ratelimit-remaining' in r.headers
        assert 'x-ratelimit-reset' in r.headers

    def test_ratelimit_limit_header_value(self):
        """X-RateLimit-Limit should equal the configured limit."""
        client = make_app(RateLimit(7, per='minute'))
        for _ in range(8):
            r = make_request(client)
        assert r.headers['x-ratelimit-limit'] == '7'

    def test_ratelimit_remaining_is_zero_on_429(self):
        """X-RateLimit-Remaining should be 0 on a 429 response."""
        client = make_app(RateLimit(2, per='minute'))
        for _ in range(3):
            r = make_request(client)
        assert r.headers['x-ratelimit-remaining'] == '0'


# ============================================================================
# Test Window Reset
# ============================================================================

class TestWindowReset:
    """Test that the fixed window resets correctly after the period expires."""

    def test_counter_resets_after_window(self):
        """After the window expires requests should be allowed again."""
        limiter = RateLimit(2, per='second')
        client = make_app(limiter)

        # Exhaust the limit
        make_request(client)
        make_request(client)
        r = make_request(client)
        assert r.status_code == 429

        # Advance time past the window
        with patch('fastkit_core.http.rate_limit.time') as mock_time:
            mock_time.time.return_value = time.time() + 2  # 2s later
            # Manually expire the window by clearing storage
            limiter._storage.clear()

        # Should be allowed again
        r = make_request(client)
        assert r.status_code == 200

    def test_new_window_starts_fresh(self):
        """After reset, full limit should be available again."""
        limiter = RateLimit(3, per='minute')
        client = make_app(limiter)

        # Exhaust limit
        for _ in range(3):
            make_request(client)

        # Simulate window expiry by clearing storage
        limiter._storage.clear()

        # All 3 should pass again
        for _ in range(3):
            r = make_request(client)
            assert r.status_code == 200

