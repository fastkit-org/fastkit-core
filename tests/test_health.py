"""
Comprehensive tests for FastKit Core Health Check module.

Tests create_health_router() factory and supporting models:
- Liveness endpoint — always 200 when process is running
- Readiness endpoint — 200 when all checks pass, 503 when any fail
- include_db=False — skips automatic DB checks
- include_version — version field present/absent
- Custom async check functions
- Multiple checks — all healthy, partial failure, all failed
- HealthCheck and HealthResponse models
- Router mounts correctly at custom paths
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastkit_core.http import (
    HealthCheck,
    HealthResponse,
    create_health_router,
)


# ============================================================================
# Helpers
# ============================================================================

def make_client(router_kwargs: dict | None = None, prefix: str = '/health') -> TestClient:
    """Create a TestClient with a mounted health router."""
    app = FastAPI()
    app.include_router(create_health_router(**(router_kwargs or {})), prefix=prefix)
    return TestClient(app, raise_server_exceptions=False)


def ok_check(name: str):
    """Factory for a custom async check that always returns ok."""
    async def _check() -> HealthCheck:
        return HealthCheck(name=name, status='ok', latency_ms=1)
    return _check


def error_check(name: str, detail: str = 'connection refused'):
    """Factory for a custom async check that always returns error."""
    async def _check() -> HealthCheck:
        return HealthCheck(name=name, status='error', detail=detail)
    return _check


def degraded_check(name: str):
    """Factory for a custom async check that returns degraded."""
    async def _check() -> HealthCheck:
        return HealthCheck(name=name, status='degraded')
    return _check


# Patch target — health_check_all and health_check_all_async live here
_DB_SYNC_PATH = 'fastkit_core.http.health.health_check_all'
_DB_ASYNC_PATH = 'fastkit_core.http.health.health_check_all_async'

ALL_HEALTHY_DB = {'default': {'primary': True, 'replica': True}}
ONE_FAILED_DB = {'default': {'primary': True, 'replica': False}}
ALL_FAILED_DB = {'default': {'primary': False}}


# ============================================================================
# Test HealthCheck Model
# ============================================================================

class TestHealthCheckModel:
    """Test the HealthCheck Pydantic model."""

    def test_ok_status(self):
        hc = HealthCheck(name='redis', status='ok')
        assert hc.status == 'ok'
        assert hc.name == 'redis'

    def test_error_status(self):
        hc = HealthCheck(name='redis', status='error', detail='timeout')
        assert hc.status == 'error'
        assert hc.detail == 'timeout'

    def test_degraded_status(self):
        hc = HealthCheck(name='cache', status='degraded')
        assert hc.status == 'degraded'

    def test_optional_fields_default_to_none(self):
        hc = HealthCheck(name='x', status='ok')
        assert hc.detail is None
        assert hc.latency_ms is None

    def test_latency_ms(self):
        hc = HealthCheck(name='api', status='ok', latency_ms=42)
        assert hc.latency_ms == 42

    def test_invalid_status_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            HealthCheck(name='x', status='unknown')

    def test_model_dump(self):
        hc = HealthCheck(name='db', status='ok', latency_ms=5)
        data = hc.model_dump()
        assert data['name'] == 'db'
        assert data['status'] == 'ok'
        assert data['latency_ms'] == 5

