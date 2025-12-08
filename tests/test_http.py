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