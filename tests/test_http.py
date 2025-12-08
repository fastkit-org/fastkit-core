"""
Comprehensive tests for FastKit Core HTTP module.

Tests all HTTP utilities:
- Response formatters (success, error, paginated)
- Custom exceptions
- Exception handlers
- Middleware (RequestID, Locale)
- Dependencies (pagination, locale)

"""

import pytest
import json
from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr, ValidationError
from starlette.responses import JSONResponse

from fastkit_core.http import (
    success_response,
    error_response,
    paginated_response,
    FastKitException,
    NotFoundException,
    ValidationException,
    UnauthorizedException,
    ForbiddenException,
    RequestIDMiddleware,
    LocaleMiddleware,
    register_exception_handlers,
    get_pagination,
    get_locale,
)
from fastkit_core.validation import BaseSchema
from fastkit_core.i18n import set_locale, set_translation_manager, TranslationManager
from fastkit_core.config import ConfigManager, set_config_manager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def translations_dir(tmp_path):
    """Create temporary translations directory."""
    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()

    # English translations
    en_content = {
        "validation": {
            "failed": "Validation failed"
        },
        "errors": {
            "internal_server_error": "Internal server error"
        }
    }

    with open(trans_dir / "en.json", "w") as f:
        json.dump(en_content, f)

    # Spanish translations
    es_content = {
        "validation": {
            "failed": "Validación fallida"
        },
        "errors": {
            "internal_server_error": "Error interno del servidor"
        }
    }

    with open(trans_dir / "es.json", "w") as f:
        json.dump(es_content, f)

    return trans_dir


@pytest.fixture
def setup_i18n(translations_dir):
    """Setup i18n with translations."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()
    config.set('app.TRANSLATIONS_PATH', str(translations_dir))
    config.set('app.DEFAULT_LANGUAGE', 'en')
    config.set('app.DEBUG', False)
    set_config_manager(config)

    manager = TranslationManager(translations_dir=translations_dir)
    set_translation_manager(manager)
    set_locale('en')

    yield

    set_locale('en')


@pytest.fixture
def app(setup_i18n):
    """Create FastAPI app with exception handlers."""
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

# ============================================================================
# Test Response Formatters
# ============================================================================
class TestSuccessResponse:
    """Test success_response formatter."""

    def test_success_basic(self):
        """Should create basic success response."""
        response = success_response()

        assert response.status_code == 200
        content = json.loads(response.body)
        assert content['success'] is True
        assert 'data' in content

    def test_success_with_data(self):
        """Should include data in response."""
        data = {'id': 1, 'name': 'Test'}
        response = success_response(data=data)

        content = json.loads(response.body)
        assert content['success'] is True
        assert content['data'] == data

    def test_success_with_message(self):
        """Should include message when provided."""
        response = success_response(message="Operation successful")

        content = json.loads(response.body)
        assert content['success'] is True
        assert content['message'] == "Operation successful"

    def test_success_without_message(self):
        """Should not include message when not provided."""
        response = success_response(data={'test': 'value'})

        content = json.loads(response.body)
        assert 'message' not in content

    def test_success_custom_status(self):
        """Should use custom status code."""
        response = success_response(status_code=201)

        assert response.status_code == 201

    def test_success_with_list_data(self):
        """Should handle list data."""
        data = [{'id': 1}, {'id': 2}]
        response = success_response(data=data)

        content = json.loads(response.body)
        assert content['data'] == data

    def test_success_with_none_data(self):
        """Should handle None data."""
        response = success_response(data=None)

        content = json.loads(response.body)
        assert content['data'] is None

    def test_success_format(self):
        """Should match expected format."""
        response = success_response(
            data={'test': 'value'},
            message="Success"
        )

        content = json.loads(response.body)
        assert 'success' in content
        assert 'data' in content
        assert 'message' in content
        assert content['success'] is True

class TestErrorResponse:
    """Test error_response formatter."""

    def test_error_basic(self):
        """Should create basic error response."""
        response = error_response(message="Error occurred")

        assert response.status_code == 400
        content = json.loads(response.body)
        assert content['success'] is False
        assert content['message'] == "Error occurred"

    def test_error_with_errors_dict(self):
        """Should include validation errors."""
        errors = {
            'email': ['Invalid email format'],
            'password': ['Too short']
        }
        response = error_response(
            message="Validation failed",
            errors=errors
        )

        content = json.loads(response.body)
        assert content['success'] is False
        assert content['errors'] == errors

    def test_error_without_errors(self):
        """Should not include errors when not provided."""
        response = error_response(message="Error")

        content = json.loads(response.body)
        assert 'errors' not in content

    def test_error_custom_status(self):
        """Should use custom status code."""
        response = error_response(message="Not found", status_code=404)

        assert response.status_code == 404

    def test_error_format(self):
        """Should match expected format."""
        response = error_response(
            message="Error",
            errors={'field': ['error']},
            status_code=422
        )

        content = json.loads(response.body)
        assert 'success' in content
        assert 'message' in content
        assert 'errors' in content
        assert content['success'] is False