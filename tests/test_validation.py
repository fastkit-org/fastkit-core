"""
Comprehensive tests for FastKit Core Validation module.

Tests BaseSchema, validation rules, and validator mixins:
- BaseSchema error formatting and translation
- Validation rules (min_length, max_length, etc.)
- PasswordValidatorMixin
- StrongPasswordValidatorMixin
- UsernameValidatorMixin
- SlugValidatorMixin

Target Coverage: 95%+
"""

import pytest
import json
from pathlib import Path
from pydantic import ValidationError, EmailStr, Field
from typing import ClassVar, Dict

from fastkit_core.validation import (
    BaseSchema,
    min_length,
    max_length,
    length,
    min_value,
    max_value,
    between,
    pattern,
    PasswordValidatorMixin,
    StrongPasswordValidatorMixin,
    UsernameValidatorMixin,
    SlugValidatorMixin,
)
from fastkit_core.i18n import set_locale, set_translation_manager, TranslationManager
from fastkit_core.config import ConfigManager, set_config_manager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def translations_dir(tmp_path):
    """Create temporary translations directory with validation messages."""
    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()

    # English validation messages
    en_content = {
        "validation": {
            "required": "The {field} field is required",
            "string_too_short": "The {field} must be at least {min_length} characters",
            "string_too_long": "The {field} must not exceed {max_length} characters",
            "value_error": "Invalid value for {field}",
            "email": "The {field} must be a valid email address",
            "url": "The {field} must be a valid URL",
            "greater_than_equal": "The {field} must be at least {ge}",
            "less_than_equal": "The {field} must not exceed {le}",
            "greater_than": "The {field} must be greater than {gt}",
            "less_than": "The {field} must be less than {lt}",
            "string_pattern_mismatch": "The {field} format is invalid",
            "password": {
                "min_length": "Password must be at least {min} characters",
                "max_length": "Password must not exceed {max} characters",
                "uppercase": "Password must contain at least one uppercase letter",
                "lowercase": "Password must contain at least one lowercase letter",
                "digit": "Password must contain at least one digit",
                "special_char": "Password must contain at least one special character"
            },
            "username": {
                "min_length": "Username must be at least {min} characters",
                "max_length": "Username must not exceed {max} characters",
                "format": "Username must start with a letter and contain only letters, numbers, and underscores"
            },
            "slug": {
                "format": "Slug must be lowercase letters, numbers, and hyphens only"
            }
        }
    }

    with open(trans_dir / "en.json", "w", encoding="utf-8") as f:
        json.dump(en_content, f, ensure_ascii=False, indent=2)

    # Spanish validation messages
    es_content = {
        "validation": {
            "required": "El campo {field} es obligatorio",
            "string_too_short": "El campo {field} debe tener al menos {min_length} caracteres",
            "string_too_long": "El campo {field} no debe exceder {max_length} caracteres",
            "value_error": "Valor inválido para {field}",
            "email": "El campo {field} debe ser un correo electrónico válido",
            "password": {
                "min_length": "La contraseña debe tener al menos {min} caracteres",
                "max_length": "La contraseña no debe exceder {max} caracteres",
                "uppercase": "La contraseña debe contener al menos una letra mayúscula",
                "special_char": "La contraseña debe contener al menos un carácter especial"
            },
            "username": {
                "min_length": "El nombre de usuario debe tener al menos {min} caracteres",
                "format": "El nombre de usuario debe comenzar con una letra y contener solo letras, números y guiones bajos"
            }
        }
    }

    with open(trans_dir / "es.json", "w", encoding="utf-8") as f:
        json.dump(es_content, f, ensure_ascii=False, indent=2)

    return trans_dir


@pytest.fixture
def setup_i18n(translations_dir):
    """Setup i18n with translations."""
    # Setup config
    config = ConfigManager(modules=[], auto_load=False)
    config.load()
    config.set('app.TRANSLATIONS_PATH', str(translations_dir))
    config.set('app.DEFAULT_LANGUAGE', 'en')
    config.set('app.FALLBACK_LANGUAGE', 'en')
    set_config_manager(config)

    # Setup translation manager
    manager = TranslationManager(translations_dir=translations_dir)
    set_translation_manager(manager)

    # Set default locale
    set_locale('en')

    yield

    # Cleanup
    set_locale('en')


# ============================================================================
# Test BaseSchema Translation
# ============================================================================

class TestBaseSchemaTranslation:
    """Test BaseSchema error translation."""

    def test_translate_required_error(self, setup_i18n):
        """Should translate 'required' error."""

        class TestSchema(BaseSchema):
            name: str

        try:
            TestSchema()
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'name' in errors
            assert 'required' in errors['name'][0].lower()

    def test_translate_min_length_error(self, setup_i18n):
        """Should translate 'min_length' error."""

        class TestSchema(BaseSchema):
            name: str = Field(min_length=5)

        try:
            TestSchema(name="abc")
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'name' in errors
            assert '5' in errors['name'][0]
            assert 'at least' in errors['name'][0].lower()

    def test_translate_max_length_error(self, setup_i18n):
        """Should translate 'max_length' error."""

        class TestSchema(BaseSchema):
            name: str = Field(max_length=10)

        try:
            TestSchema(name="a" * 20)
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'name' in errors
            assert '10' in errors['name'][0]
            assert 'exceed' in errors['name'][0].lower()

    def test_translate_email_error(self, setup_i18n):
        """Should translate email validation error."""

        class TestSchema(BaseSchema):
            email: EmailStr

        try:
            TestSchema(email="not_an_email")
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'email' in errors
            assert 'email' in errors['email'][0].lower()

    def test_translate_custom_error(self, setup_i18n):
        """Should translate custom validator errors."""

        class TestSchema(BaseSchema):
            age: int = Field(ge=18)

        try:
            TestSchema(age=15)
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'age' in errors
            assert '18' in errors['age'][0]

    def test_fallback_to_default_message(self, setup_i18n):
        """Should fallback to Pydantic message when translation missing."""

        class TestSchema(BaseSchema):
            # Use error type not in translation map
            value: int

        try:
            TestSchema(value="not_a_number")
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'value' in errors
            # Should have some error message
            assert len(errors['value'][0]) > 0

    def test_translate_in_spanish(self, setup_i18n):
        """Should translate errors in Spanish."""
        set_locale('es')

        class TestSchema(BaseSchema):
            name: str

        try:
            TestSchema()
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'name' in errors
            # Should contain Spanish words
            assert 'obligatorio' in errors['name'][0].lower()

    def test_translate_with_field_context(self, setup_i18n):
        """Should include field name in translation."""

        class TestSchema(BaseSchema):
            username: str

        try:
            TestSchema()
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'username' in errors
            assert 'username' in errors['username'][0].lower()