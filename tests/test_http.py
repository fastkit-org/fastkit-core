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

class TestPaginatedResponse:
    """Test paginated_response formatter."""

    def test_paginated_basic(self):
        """Should create paginated response."""
        items = [{'id': 1}, {'id': 2}]
        pagination = {
            'page': 1,
            'per_page': 20,
            'total': 2,
            'total_pages': 1,
            'has_next': False,
            'has_prev': False
        }

        response = paginated_response(items=items, pagination=pagination)

        assert response.status_code == 200
        content = json.loads(response.body)
        assert content['success'] is True
        assert content['data'] == items
        assert content['pagination'] == pagination

    def test_paginated_with_message(self):
        """Should include message when provided."""
        response = paginated_response(
            items=[],
            pagination={'page': 1, 'total': 0},
            message="No results"
        )

        content = json.loads(response.body)
        assert content['message'] == "No results"

    def test_paginated_without_message(self):
        """Should not include message when not provided."""
        response = paginated_response(
            items=[],
            pagination={'page': 1}
        )

        content = json.loads(response.body)
        assert 'message' not in content

    def test_paginated_empty_items(self):
        """Should handle empty items list."""
        response = paginated_response(
            items=[],
            pagination={'page': 1, 'total': 0}
        )

        content = json.loads(response.body)
        assert content['data'] == []

    def test_paginated_format(self):
        """Should match expected format."""
        response = paginated_response(
            items=[{'id': 1}],
            pagination={'page': 1, 'per_page': 10, 'total': 100}
        )

        content = json.loads(response.body)
        assert 'success' in content
        assert 'data' in content
        assert 'pagination' in content
        assert content['success'] is True

    def test_paginated_custom_status(self):
        """Should use custom status code."""
        response = paginated_response(
            items=[],
            pagination={'page': 1},
            status_code=206
        )

        assert response.status_code == 206

# ============================================================================
# Test Custom Exceptions
# ============================================================================
class TestExceptions:
    """Test custom exception classes."""

    def test_fastkit_exception_basic(self):
        """Should create FastKitException."""
        exc = FastKitException(message="Error occurred")

        assert exc.message == "Error occurred"
        assert exc.status_code == 400
        assert exc.errors is None

    def test_fastkit_exception_custom_status(self):
        """Should accept custom status code."""
        exc = FastKitException(message="Error", status_code=500)

        assert exc.status_code == 500

    def test_fastkit_exception_with_errors(self):
        """Should include errors dict."""
        errors = {'field': ['error']}
        exc = FastKitException(message="Error", errors=errors)

        assert exc.errors == errors

    def test_not_found_exception(self):
        """Should create 404 exception."""
        exc = NotFoundException()

        assert exc.status_code == 404
        assert "not found" in exc.message.lower()

    def test_not_found_exception_custom_message(self):
        """Should accept custom message."""
        exc = NotFoundException(message="User not found")

        assert exc.message == "User not found"
        assert exc.status_code == 404

    def test_validation_exception(self):
        """Should create 422 exception."""
        errors = {'email': ['Invalid']}
        exc = ValidationException(errors=errors)

        assert exc.status_code == 422
        assert exc.errors == errors
        assert "validation" in exc.message.lower()

    def test_validation_exception_custom_message(self):
        """Should accept custom message."""
        exc = ValidationException(
            errors={'field': ['error']},
            message="Custom validation error"
        )

        assert exc.message == "Custom validation error"

    def test_unauthorized_exception(self):
        """Should create 401 exception."""
        exc = UnauthorizedException()

        assert exc.status_code == 401
        assert "unauthorized" in exc.message.lower()

    def test_unauthorized_exception_custom_message(self):
        """Should accept custom message."""
        exc = UnauthorizedException(message="Token expired")

        assert exc.message == "Token expired"

    def test_forbidden_exception(self):
        """Should create 403 exception."""
        exc = ForbiddenException()

        assert exc.status_code == 403
        assert "forbidden" in exc.message.lower()

    def test_forbidden_exception_custom_message(self):
        """Should accept custom message."""
        exc = ForbiddenException(message="No permission")

        assert exc.message == "No permission"

# ============================================================================
# Test Exception Handlers
# ============================================================================
class TestExceptionHandlers:
    """Test exception handlers registration."""

    def test_register_exception_handlers(self, app):
        """Should register all handlers."""
        # Handlers should be registered
        assert FastKitException in app.exception_handlers

    def test_handle_fastkit_exception(self, app, client):
        """Should handle FastKitException."""

        @app.get("/test")
        def test_route():
            raise NotFoundException("Resource not found")

        response = client.get("/test")

        assert response.status_code == 404
        data = response.json()
        assert data['success'] is False
        assert "not found" in data['message'].lower()

    def test_handle_fastkit_exception_with_errors(self, app, client):
        """Should include errors in response."""

        @app.get("/test")
        def test_route():
            raise ValidationException(
                errors={'field': ['error']},
                message="Validation failed"
            )

        response = client.get("/test")

        assert response.status_code == 422
        data = response.json()
        assert data['success'] is False
        assert 'errors' in data
        assert data['errors'] == {'field': ['error']}

    def test_handle_pydantic_validation_error(self, app, client):
        """Should handle Pydantic ValidationError."""

        class TestSchema(BaseSchema):
            email: EmailStr

        @app.post("/test")
        def test_route(data: TestSchema):
            return {"ok": True}

        response = client.post("/test", json={"email": "invalid"})

        assert response.status_code == 422
        data = response.json()
        assert data['success'] is False
        assert 'errors' in data

    def test_handle_fastapi_validation_error(self, app, client):
        """Should handle FastAPI request validation."""

        @app.get("/test")
        def test_route(age: int):
            return {"age": age}

        response = client.get("/test?age=invalid")

        assert response.status_code == 422
        data = response.json()
        assert data['success'] is False

    def test_handle_generic_exception_debug_mode(self, setup_i18n):
        """Should show error details in debug mode."""
        # Create fresh app for this test
        from fastapi import FastAPI
        from fastkit_core.config import get_config_manager

        # Set debug mode BEFORE creating app
        config = get_config_manager()
        config.set('app.DEBUG', True)

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def test_route():
            raise ValueError("Something went wrong")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")

        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False
        assert "Something went wrong" in data['message']

    def test_handle_generic_exception_production_mode(self, setup_i18n):
        """Should hide error details in production."""
        # Create fresh app for this test
        from fastapi import FastAPI
        from fastkit_core.config import get_config_manager

        # Set production mode BEFORE creating app
        config = get_config_manager()
        config.set('app.DEBUG', False)

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def test_route():
            raise ValueError("Internal details")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")

        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False
        # Should not expose internal error
        assert "Internal details" not in data['message']
        # Should show generic error message
        assert "Internal server error" in data['message'] or "error" in data['message'].lower()

# ============================================================================
# Test Middleware
# ============================================================================
class TestRequestIDMiddleware:
    """Test RequestIDMiddleware."""

    def test_add_request_id_to_response(self):
        """Should add X-Request-ID header to response."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        def test_route():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")

        assert 'X-Request-ID' in response.headers
        assert len(response.headers['X-Request-ID']) > 0

    def test_request_id_unique(self):
        """Should generate unique IDs for each request."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        def test_route():
            return {"ok": True}

        client = TestClient(app)

        response1 = client.get("/test")
        response2 = client.get("/test")

        id1 = response1.headers['X-Request-ID']
        id2 = response2.headers['X-Request-ID']

        assert id1 != id2

    def test_request_id_in_state(self):
        """Should add request_id to request.state."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        captured_id = None

        @app.get("/test")
        def test_route(request: Request):
            nonlocal captured_id
            captured_id = request.state.request_id
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")

        assert captured_id is not None
        assert captured_id == response.headers['X-Request-ID']

    def test_request_id_format(self):
        """Should be valid UUID format."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        def test_route():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")

        request_id = response.headers['X-Request-ID']

        # Should be UUID format (with hyphens)
        parts = request_id.split('-')
        assert len(parts) == 5

class TestLocaleMiddleware:
    """Test LocaleMiddleware."""

    def test_locale_from_accept_language_header(self, setup_i18n):
        """Should detect locale from Accept-Language header."""
        app = FastAPI()
        app.add_middleware(LocaleMiddleware)

        detected_locale = None

        @app.get("/test")
        def test_route():
            from fastkit_core.i18n import get_locale
            nonlocal detected_locale
            detected_locale = get_locale()
            return {"ok": True}

        client = TestClient(app)
        client.get("/test", headers={"Accept-Language": "es-ES"})

        assert detected_locale == "es"

    def test_locale_from_query_parameter(self, setup_i18n):
        """Should detect locale from query parameter."""
        app = FastAPI()
        app.add_middleware(LocaleMiddleware)

        detected_locale = None

        @app.get("/test")
        def test_route():
            from fastkit_core.i18n import get_locale
            nonlocal detected_locale
            detected_locale = get_locale()
            return {"ok": True}

        client = TestClient(app)
        client.get("/test?lang=fr")

        assert detected_locale == "fr"

    def test_locale_from_cookie(self, setup_i18n):
        """Should detect locale from cookie."""
        app = FastAPI()
        app.add_middleware(LocaleMiddleware)

        detected_locale = None

        @app.get("/test")
        def test_route():
            from fastkit_core.i18n import get_locale
            nonlocal detected_locale
            detected_locale = get_locale()
            return {"ok": True}

        client = TestClient(app)
        client.get("/test", cookies={"locale": "de"})

        assert detected_locale == "de"

    def test_locale_priority(self, setup_i18n):
        """Should prioritize Accept-Language header."""
        app = FastAPI()
        app.add_middleware(LocaleMiddleware)

        detected_locale = None

        @app.get("/test")
        def test_route():
            from fastkit_core.i18n import get_locale
            nonlocal detected_locale
            detected_locale = get_locale()
            return {"ok": True}

        client = TestClient(app)
        # Header should take precedence over cookie
        client.get(
            "/test",
            headers={"Accept-Language": "es-ES"},
            cookies={"locale": "fr"}
        )

        assert detected_locale == "es"

    def test_locale_default_fallback(self, setup_i18n):
        """Should fallback to default locale."""
        app = FastAPI()
        app.add_middleware(LocaleMiddleware)

        detected_locale = None

        @app.get("/test")
        def test_route():
            from fastkit_core.i18n import get_locale
            nonlocal detected_locale
            detected_locale = get_locale()
            return {"ok": True}

        client = TestClient(app)
        client.get("/test")

        assert detected_locale == "en"  # Default


# ============================================================================
# Test Dependencies
# ============================================================================
class TestDependencies:
    """Test FastAPI dependencies."""

    def test_get_pagination_default(self):
        """Should provide default pagination params."""
        result = get_pagination()

        assert result['page'] == 1
        assert result['per_page'] == 20
        assert result['offset'] == 0

    def test_get_pagination_custom(self):
        """Should accept custom pagination params."""
        result = get_pagination(page=3, per_page=50)

        assert result['page'] == 3
        assert result['per_page'] == 50
        assert result['offset'] == 100  # (3-1) * 50

    def test_get_pagination_calculates_offset(self):
        """Should calculate correct offset."""
        result = get_pagination(page=5, per_page=10)

        assert result['offset'] == 40

    def test_get_pagination_in_route(self):
        """Should work as FastAPI dependency."""
        app = FastAPI()

        @app.get("/test")
        def test_route(pagination: dict = Depends(get_pagination)):
            return pagination

        client = TestClient(app)
        response = client.get("/test?page=2&per_page=15")

        data = response.json()
        assert data['page'] == 2
        assert data['per_page'] == 15

    def test_get_pagination_validation(self):
        """Should validate pagination params."""
        app = FastAPI()

        @app.get("/test")
        def test_route(pagination: dict = Depends(get_pagination)):
            return pagination

        client = TestClient(app)

        # Page must be >= 1
        response = client.get("/test?page=0")
        assert response.status_code == 422

        # Per page must be <= 100
        response = client.get("/test?per_page=200")
        assert response.status_code == 422

    def test_get_locale_from_query(self, setup_i18n):
        """Should get locale from query parameter."""
        result = get_locale(locale="es")

        assert result == "es"

    def test_get_locale_from_context(self, setup_i18n):
        """Should get locale from context when not in query."""
        from fastkit_core.i18n import set_locale
        set_locale('fr')

        result = get_locale(locale=None)

        assert result == "fr"

    def test_get_locale_in_route(self, setup_i18n):
        """Should work as FastAPI dependency."""
        app = FastAPI()

        @app.get("/test")
        def test_route(locale: str = Depends(get_locale)):
            return {"locale": locale}

        client = TestClient(app)
        response = client.get("/test?locale=es")

        data = response.json()
        assert data['locale'] == "es"


# ============================================================================
# Test Integration Scenarios
# ============================================================================
class TestIntegration:
    """Test real-world integration scenarios."""

    def test_complete_api_flow(self, app, client):
        """Should handle complete API request/response flow."""
        app.add_middleware(RequestIDMiddleware)
        app.add_middleware(LocaleMiddleware)

        @app.post("/users")
        def create_user(request: Request):
            # Access request ID
            request_id = request.state.request_id

            return success_response(
                data={'id': 1, 'name': 'John', 'request_id': request_id},
                message="User created"
            )

        response = client.post("/users", json={'name': 'John'})

        assert response.status_code == 200
        assert 'X-Request-ID' in response.headers
        data = response.json()
        assert data['success'] is True
        assert data['data']['name'] == 'John'
        assert data['message'] == "User created"

    def test_pagination_flow(self, app, client):
        """Should handle paginated API response."""

        @app.get("/items")
        def get_items(pagination: dict = Depends(get_pagination)):
            # Simulate paginated data
            items = [{'id': i} for i in range(10)]
            meta = {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': 100,
                'total_pages': 10,
                'has_next': True,
                'has_prev': False
            }
            return paginated_response(items=items, pagination=meta)

        response = client.get("/items?page=1&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 10
        assert 'pagination' in data
        assert data['pagination']['page'] == 1

    def test_error_handling_flow(self, app, client):
        """Should handle errors gracefully."""

        @app.get("/users/{user_id}")
        def get_user(user_id: int):
            if user_id == 999:
                raise NotFoundException("User not found")
            return success_response(data={'id': user_id})

        # Success case
        response = client.get("/users/1")
        assert response.status_code == 200

        # Error case
        response = client.get("/users/999")
        assert response.status_code == 404
        data = response.json()
        assert data['success'] is False
        assert "not found" in data['message'].lower()

    def test_validation_flow(self, app, client):
        """Should handle validation errors."""

        class UserCreate(BaseSchema):
            email: EmailStr
            age: int

        @app.post("/users")
        def create_user(data: UserCreate):
            return success_response(data=data.model_dump())

        # Valid data
        response = client.post("/users", json={
            "email": "test@example.com",
            "age": 25
        })
        assert response.status_code == 200

        # Invalid email
        response = client.post("/users", json={
            "email": "invalid",
            "age": 25
        })
        assert response.status_code == 422
        data = response.json()
        assert data['success'] is False
        assert 'errors' in data

    def test_multilingual_api(self, app, client, setup_i18n):
        """Should support multiple languages."""
        app.add_middleware(LocaleMiddleware)

        @app.get("/error")
        def error_route():
            from fastkit_core.i18n import _
            raise FastKitException(_('validation.failed'))

        # English
        response = client.get("/error", headers={"Accept-Language": "en"})
        data = response.json()
        assert "Validation failed" in data['message']

        # Spanish
        response = client.get("/error", headers={"Accept-Language": "es"})
        data = response.json()
        assert "Validación fallida" in data['message']


# ============================================================================
# Test Edge Cases
# ============================================================================
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_response_with_empty_data(self):
        """Should handle empty data structures."""
        response = success_response(data={})
        content = json.loads(response.body)
        assert content['data'] == {}

    def test_response_with_complex_nested_data(self):
        """Should handle complex nested structures."""
        data = {
            'user': {
                'profile': {
                    'settings': {
                        'theme': 'dark'
                    }
                }
            }
        }
        response = success_response(data=data)
        content = json.loads(response.body)
        assert content['data'] == data

    def test_exception_with_empty_message(self):
        """Should handle empty error message."""
        exc = FastKitException(message="")
        assert exc.message == ""

    def test_pagination_with_zero_items(self):
        """Should handle empty pagination."""
        response = paginated_response(
            items=[],
            pagination={
                'page': 1,
                'per_page': 20,
                'total': 0,
                'total_pages': 0,
                'has_next': False,
                'has_prev': False
            }
        )
        content = json.loads(response.body)
        assert content['data'] == []
        assert content['pagination']['total'] == 0

    def test_locale_with_empty_header(self, setup_i18n):
        """Should handle empty Accept-Language header."""
        app = FastAPI()
        app.add_middleware(LocaleMiddleware)

        @app.get("/test")
        def test_route():
            from fastkit_core.i18n import get_locale
            return {"locale": get_locale()}

        client = TestClient(app)
        response = client.get("/test", headers={"Accept-Language": ""})

        # Should fallback to default
        data = response.json()
        assert data['locale'] == "en"

    def test_pagination_with_invalid_types(self):
        """Should validate pagination parameter types."""
        app = FastAPI()

        @app.get("/test")
        def test_route(pagination: dict = Depends(get_pagination)):
            return pagination

        client = TestClient(app)

        # String instead of int
        response = client.get("/test?page=abc")
        assert response.status_code == 422