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

# ============================================================================
# Test HealthResponse Model
# ============================================================================

class TestHealthResponseModel:
    """Test the HealthResponse Pydantic model."""

    def test_default_checks_empty(self):
        hr = HealthResponse(status='ok')
        assert hr.checks == []

    def test_version_optional(self):
        hr = HealthResponse(status='ok')
        assert hr.version is None

    def test_with_checks(self):
        checks = [HealthCheck(name='db', status='ok')]
        hr = HealthResponse(status='ok', checks=checks)
        assert len(hr.checks) == 1

    def test_with_version(self):
        hr = HealthResponse(status='ok', version='1.2.3')
        assert hr.version == '1.2.3'

# ============================================================================
# Test Liveness Endpoint
# ============================================================================

class TestLiveness:
    """GET /health — liveness probe, always 200."""

    def test_returns_200(self):
        client = make_client({'include_db': False})
        r = client.get('/health/')
        assert r.status_code == 200

    def test_body_status_ok(self):
        client = make_client({'include_db': False})
        data = client.get('/health/').json()
        assert data['status'] == 'ok'

    def test_no_checks_in_liveness(self):
        """Liveness must not run any checks — just confirm process is alive."""
        client = make_client({'include_db': False})
        data = client.get('/health/').json()
        assert data.get('checks', []) == []

    def test_version_present_by_default(self):
        client = make_client({'include_db': False})
        data = client.get('/health/').json()
        assert 'version' in data
        assert data['version'] is not None

    def test_version_absent_when_disabled(self):
        client = make_client({'include_db': False, 'include_version': False})
        data = client.get('/health/').json()
        assert data.get('version') is None

    def test_custom_liveness_path(self):
        app = FastAPI()
        app.include_router(
            create_health_router(include_db=False, liveness_path='/live'),
            prefix='/health'
        )
        client = TestClient(app)
        r = client.get('/health/live')
        assert r.status_code == 200

# ============================================================================
# Test Readiness Endpoint — No DB, Custom Checks Only
# ============================================================================

class TestReadinessNoDb:
    """GET /health/ready with include_db=False — only custom checks run."""

    def test_returns_200_with_no_checks(self):
        client = make_client({'include_db': False})
        r = client.get('/health/ready')
        assert r.status_code == 200

    def test_body_ok_with_no_checks(self):
        client = make_client({'include_db': False})
        data = client.get('/health/ready').json()
        assert data['status'] == 'ok'
        assert data['checks'] == []

    def test_returns_200_when_all_custom_checks_pass(self):
        client = make_client({
            'include_db': False,
            'checks': [ok_check('redis'), ok_check('stripe')],
        })
        r = client.get('/health/ready')
        assert r.status_code == 200

    def test_body_contains_check_results(self):
        client = make_client({
            'include_db': False,
            'checks': [ok_check('redis')],
        })
        data = client.get('/health/ready').json()
        assert len(data['checks']) == 1
        assert data['checks'][0]['name'] == 'redis'
        assert data['checks'][0]['status'] == 'ok'

    def test_returns_503_when_one_check_fails(self):
        client = make_client({
            'include_db': False,
            'checks': [ok_check('redis'), error_check('stripe')],
        })
        r = client.get('/health/ready')
        assert r.status_code == 503

    def test_body_status_error_on_503(self):
        client = make_client({
            'include_db': False,
            'checks': [error_check('stripe')],
        })
        data = client.get('/health/ready').json()
        assert data['status'] == 'error'

    def test_returns_503_when_all_checks_fail(self):
        client = make_client({
            'include_db': False,
            'checks': [error_check('redis'), error_check('stripe')],
        })
        r = client.get('/health/ready')
        assert r.status_code == 503

    def test_degraded_does_not_cause_503(self):
        """degraded status should not trigger 503 — only 'error' does."""
        client = make_client({
            'include_db': False,
            'checks': [ok_check('redis'), degraded_check('cache')],
        })
        r = client.get('/health/ready')
        assert r.status_code == 200

    def test_failed_check_detail_in_response(self):
        client = make_client({
            'include_db': False,
            'checks': [error_check('stripe', detail='API key invalid')],
        })
        data = client.get('/health/ready').json()
        failed = next(c for c in data['checks'] if c['name'] == 'stripe')
        assert failed['detail'] == 'API key invalid'

    def test_version_present_in_readiness(self):
        client = make_client({'include_db': False})
        data = client.get('/health/ready').json()
        assert data.get('version') is not None

    def test_version_absent_when_disabled(self):
        client = make_client({'include_db': False, 'include_version': False})
        data = client.get('/health/ready').json()
        assert data.get('version') is None

    def test_custom_readiness_path(self):
        app = FastAPI()
        app.include_router(
            create_health_router(include_db=False, readiness_path='/ready-check'),
            prefix='/health'
        )
        client = TestClient(app)
        r = client.get('/health/ready-check')
        assert r.status_code == 200


# ============================================================================
# Test Readiness Endpoint — Sync DB Checks
# ============================================================================

class TestReadinessSyncDb:
    """GET /health/ready with include_db=True, is_db_async=False."""

    def test_200_when_all_connections_healthy(self):
        with patch(_DB_SYNC_PATH, return_value=ALL_HEALTHY_DB):
            client = make_client({'include_db': True, 'is_db_async': False})
            r = client.get('/health/ready')
        assert r.status_code == 200

    def test_503_when_one_connection_fails(self):
        with patch(_DB_SYNC_PATH, return_value=ONE_FAILED_DB):
            client = make_client({'include_db': True, 'is_db_async': False})
            r = client.get('/health/ready')
        assert r.status_code == 503

    def test_db_check_appears_in_checks(self):
        with patch(_DB_SYNC_PATH, return_value=ALL_HEALTHY_DB):
            client = make_client({'include_db': True, 'is_db_async': False})
            data = client.get('/health/ready').json()
        names = [c['name'] for c in data['checks']]
        assert 'database:default' in names

    def test_include_db_false_skips_sync_db(self):
        with patch(_DB_SYNC_PATH, return_value=ALL_FAILED_DB) as mock:
            client = make_client({'include_db': False, 'is_db_async': False})
            client.get('/health/ready')
        mock.assert_not_called()

# ============================================================================
# Test Readiness Endpoint — Async DB Checks
# ============================================================================

class TestReadinessAsyncDb:
    """GET /health/ready with include_db=True, is_db_async=True (default)."""

    def test_200_when_all_connections_healthy(self):
        async_mock = AsyncMock(return_value=ALL_HEALTHY_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({'include_db': True, 'is_db_async': True})
            r = client.get('/health/ready')
        assert r.status_code == 200

    def test_503_when_one_connection_fails(self):
        async_mock = AsyncMock(return_value=ONE_FAILED_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({'include_db': True, 'is_db_async': True})
            r = client.get('/health/ready')
        assert r.status_code == 503

    def test_db_check_status_ok_in_body(self):
        async_mock = AsyncMock(return_value=ALL_HEALTHY_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({'include_db': True, 'is_db_async': True})
            data = client.get('/health/ready').json()
        db_check = next(c for c in data['checks'] if c['name'] == 'database:default')
        assert db_check['status'] == 'ok'

    def test_db_check_status_error_in_body(self):
        async_mock = AsyncMock(return_value=ONE_FAILED_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({'include_db': True, 'is_db_async': True})
            data = client.get('/health/ready').json()
        db_check = next(c for c in data['checks'] if c['name'] == 'database:default')
        assert db_check['status'] == 'error'

    def test_include_db_false_skips_async_db(self):
        async_mock = AsyncMock(return_value=ALL_FAILED_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({'include_db': False, 'is_db_async': True})
            r = client.get('/health/ready')
        async_mock.assert_not_called()
        assert r.status_code == 200

# ============================================================================
# Test Combined — Custom Checks + DB
# ============================================================================

class TestReadinessCombined:
    """Custom checks and DB checks together."""

    def test_200_when_both_custom_and_db_pass(self):
        async_mock = AsyncMock(return_value=ALL_HEALTHY_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({
                'include_db': True,
                'is_db_async': True,
                'checks': [ok_check('redis')],
            })
            data = client.get('/health/ready').json()
        assert data['status'] == 'ok'
        assert len(data['checks']) == 2  # redis + database:default

    def test_503_when_custom_fails_but_db_passes(self):
        async_mock = AsyncMock(return_value=ALL_HEALTHY_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({
                'include_db': True,
                'is_db_async': True,
                'checks': [error_check('stripe')],
            })
            r = client.get('/health/ready')
        assert r.status_code == 503

    def test_503_when_db_fails_but_custom_passes(self):
        async_mock = AsyncMock(return_value=ALL_FAILED_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({
                'include_db': True,
                'is_db_async': True,
                'checks': [ok_check('redis')],
            })
            r = client.get('/health/ready')
        assert r.status_code == 503

    def test_all_checks_present_in_body(self):
        async_mock = AsyncMock(return_value=ALL_HEALTHY_DB)
        with patch(_DB_ASYNC_PATH, async_mock):
            client = make_client({
                'include_db': True,
                'is_db_async': True,
                'checks': [ok_check('redis'), ok_check('stripe')],
            })
            data = client.get('/health/ready').json()
        names = [c['name'] for c in data['checks']]
        assert 'redis' in names
        assert 'stripe' in names
        assert 'database:default' in names

# ============================================================================
# Test Router Factory
# ============================================================================

class TestCreateHealthRouter:
    """Test the factory function itself."""

    def test_returns_api_router(self):
        from fastapi import APIRouter
        router = create_health_router(include_db=False)
        assert isinstance(router, APIRouter)

    def test_default_prefix_mount(self):
        """Router mounts correctly at /health prefix."""
        app = FastAPI()
        app.include_router(create_health_router(include_db=False), prefix='/health')
        client = TestClient(app)
        r = client.get('/health/')
        assert r.status_code == 200

    def test_different_prefix(self):
        app = FastAPI()
        app.include_router(create_health_router(include_db=False), prefix='/status')
        client = TestClient(app)
        assert client.get('/status/').status_code == 200
        assert client.get('/health/').status_code == 404

    def test_multiple_routers_independent(self):
        """Two health routers with different configs must be independent."""
        app = FastAPI()
        app.include_router(
            create_health_router(include_db=False, liveness_path='/live'),
            prefix='/health'
        )
        app.include_router(
            create_health_router(include_db=False, liveness_path='/ping'),
            prefix='/status'
        )
        client = TestClient(app)
        assert client.get('/health/live').status_code == 200
        assert client.get('/status/ping').status_code == 200