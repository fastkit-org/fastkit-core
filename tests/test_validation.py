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


# ============================================================================
# Test Validation Rules
# ============================================================================

class TestValidationRules:
    """Test validation rule helpers."""

    def test_min_length_rule(self, setup_i18n):
        """Should validate minimum length."""

        class TestSchema(BaseSchema):
            name: str = min_length(5)

        # Valid
        schema = TestSchema(name="hello")
        assert schema.name == "hello"

        # Invalid
        with pytest.raises(ValidationError):
            TestSchema(name="hi")

    def test_max_length_rule(self, setup_i18n):
        """Should validate maximum length."""

        class TestSchema(BaseSchema):
            name: str = max_length(10)

        # Valid
        schema = TestSchema(name="hello")
        assert schema.name == "hello"

        # Invalid
        with pytest.raises(ValidationError):
            TestSchema(name="a" * 20)

    def test_length_range_rule(self, setup_i18n):
        """Should validate length range."""

        class TestSchema(BaseSchema):
            name: str = length(3, 10)

        # Valid
        schema = TestSchema(name="hello")
        assert schema.name == "hello"

        # Too short
        with pytest.raises(ValidationError):
            TestSchema(name="ab")

        # Too long
        with pytest.raises(ValidationError):
            TestSchema(name="a" * 20)

    def test_min_value_rule(self, setup_i18n):
        """Should validate minimum value."""

        class TestSchema(BaseSchema):
            age: int = min_value(18)

        # Valid
        schema = TestSchema(age=25)
        assert schema.age == 25

        # Invalid
        with pytest.raises(ValidationError):
            TestSchema(age=15)

    def test_max_value_rule(self, setup_i18n):
        """Should validate maximum value."""

        class TestSchema(BaseSchema):
            score: int = max_value(100)

        # Valid
        schema = TestSchema(score=95)
        assert schema.score == 95

        # Invalid
        with pytest.raises(ValidationError):
            TestSchema(score=150)

    def test_between_rule(self, setup_i18n):
        """Should validate value range."""

        class TestSchema(BaseSchema):
            age: int = between(18, 100)

        # Valid
        schema = TestSchema(age=25)
        assert schema.age == 25

        # Too low
        with pytest.raises(ValidationError):
            TestSchema(age=15)

        # Too high
        with pytest.raises(ValidationError):
            TestSchema(age=150)

    def test_pattern_rule(self, setup_i18n):
        """Should validate regex pattern."""

        class TestSchema(BaseSchema):
            code: str = pattern(r'^[A-Z]{3}\d{3}$')

        # Valid
        schema = TestSchema(code="ABC123")
        assert schema.code == "ABC123"

        # Invalid
        with pytest.raises(ValidationError):
            TestSchema(code="abc123")

        with pytest.raises(ValidationError):
            TestSchema(code="ABCD1234")

    def test_float_between_rule(self, setup_i18n):
        """Should validate float ranges."""

        class TestSchema(BaseSchema):
            rating: float = between(0.0, 5.0)

        # Valid
        schema = TestSchema(rating=4.5)
        assert schema.rating == 4.5

        # Invalid
        with pytest.raises(ValidationError):
            TestSchema(rating=6.0)


# ============================================================================
# Test PasswordValidatorMixin
# ============================================================================

class TestPasswordValidator:
    """Test PasswordValidatorMixin."""

    def test_password_valid(self, setup_i18n):
        """Should accept valid password."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        schema = UserSchema(password="Test123!")
        assert schema.password == "Test123!"

    def test_password_min_length(self, setup_i18n):
        """Should enforce minimum length."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(password="Test1!")

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'password' in errors
        assert '8' in errors['password'][0]

    def test_password_max_length(self, setup_i18n):
        """Should enforce maximum length."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(password="Test123!" * 10)

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'password' in errors
        assert '16' in errors['password'][0]

    def test_password_uppercase_required(self, setup_i18n):
        """Should require uppercase letter."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(password="test123!")

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'password' in errors
        assert 'uppercase' in errors['password'][0].lower()

    def test_password_special_char_required(self, setup_i18n):
        """Should require special character."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(password="Test1234")

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'password' in errors
        assert 'special' in errors['password'][0].lower()

    def test_password_all_special_chars(self, setup_i18n):
        """Should accept all defined special characters."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        special_chars = '!@#$%^&*(),.?":{}|<>'

        for char in special_chars:
            schema = UserSchema(password=f"Test123{char}")
            assert schema.password == f"Test123{char}"

    def test_password_custom_length(self, setup_i18n):
        """Should allow custom length requirements."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            PWD_MIN_LENGTH: ClassVar[int] = 6
            PWD_MAX_LENGTH: ClassVar[int] = 10
            password: str

        # Valid with custom length
        schema = UserSchema(password="Test12!")
        assert schema.password == "Test12!"

    def test_password_translated_errors(self, setup_i18n):
        """Should translate password errors."""
        set_locale('es')

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(password="test")

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'password' in errors
        # Spanish translation
        assert 'contraseña' in errors['password'][0].lower()


# ============================================================================
# Test StrongPasswordValidatorMixin
# ============================================================================

class TestStrongPasswordValidator:
    """Test StrongPasswordValidatorMixin."""

    def test_strong_password_valid(self, setup_i18n):
        """Should accept valid strong password."""

        class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
            password: str

        schema = UserSchema(password="Test12345!")
        assert schema.password == "Test12345!"

    def test_strong_password_min_length(self, setup_i18n):
        """Should enforce 10 character minimum."""

        class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(password="Test123!")

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'password' in errors
        assert '10' in errors['password'][0]

    def test_strong_password_uppercase_required(self, setup_i18n):
        """Should require uppercase letter."""

        class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError):
            UserSchema(password="test12345!")

    def test_strong_password_lowercase_required(self, setup_i18n):
        """Should require lowercase letter."""

        class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError):
            UserSchema(password="TEST12345!")

    def test_strong_password_digit_required(self, setup_i18n):
        """Should require digit."""

        class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError):
            UserSchema(password="TestPassword!")

    def test_strong_password_special_required(self, setup_i18n):
        """Should require special character."""

        class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
            password: str

        with pytest.raises(ValidationError):
            UserSchema(password="Test1234567")

    def test_strong_password_all_requirements(self, setup_i18n):
        """Should enforce all requirements together."""

        class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
            password: str

        # Missing uppercase
        with pytest.raises(ValidationError):
            UserSchema(password="test12345!")

        # Missing lowercase
        with pytest.raises(ValidationError):
            UserSchema(password="TEST12345!")

        # Missing digit
        with pytest.raises(ValidationError):
            UserSchema(password="TestTest!!")

        # Missing special
        with pytest.raises(ValidationError):
            UserSchema(password="Test123456")

        # Valid - has all
        schema = UserSchema(password="Test12345!")
        assert schema.password == "Test12345!"


# ============================================================================
# Test UsernameValidatorMixin
# ============================================================================

class TestUsernameValidator:
    """Test UsernameValidatorMixin."""

    def test_username_valid(self, setup_i18n):
        """Should accept valid username."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        schema = UserSchema(username="john_doe123")
        assert schema.username == "john_doe123"

    def test_username_min_length(self, setup_i18n):
        """Should enforce minimum 3 characters."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(username="ab")

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'username' in errors
        assert '3' in errors['username'][0]

    def test_username_max_length(self, setup_i18n):
        """Should enforce maximum 20 characters."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(username="a" * 25)

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'username' in errors
        assert '20' in errors['username'][0]

    def test_username_must_start_with_letter(self, setup_i18n):
        """Should require starting with letter."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        # Invalid - starts with number
        with pytest.raises(ValidationError):
            UserSchema(username="123john")

        # Invalid - starts with underscore
        with pytest.raises(ValidationError):
            UserSchema(username="_john")

    def test_username_alphanumeric_underscore_only(self, setup_i18n):
        """Should allow only alphanumeric and underscore."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        # Valid
        schema = UserSchema(username="john_doe_123")
        assert schema.username == "john_doe_123"

        # Invalid - hyphen
        with pytest.raises(ValidationError):
            UserSchema(username="john-doe")

        # Invalid - special chars
        with pytest.raises(ValidationError):
            UserSchema(username="john@doe")

        # Invalid - space
        with pytest.raises(ValidationError):
            UserSchema(username="john doe")

    def test_username_case_insensitive(self, setup_i18n):
        """Should accept both cases."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        schema1 = UserSchema(username="JohnDoe")
        assert schema1.username == "JohnDoe"

        schema2 = UserSchema(username="johndoe")
        assert schema2.username == "johndoe"

    def test_username_custom_length(self, setup_i18n):
        """Should allow custom length requirements."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            USM_MIN_LENGTH: ClassVar[int] = 5
            USM_MAX_LENGTH: ClassVar[int] = 15
            username: str

        # Valid with custom length
        schema = UserSchema(username="johndoe")
        assert schema.username == "johndoe"

        # Too short
        with pytest.raises(ValidationError):
            UserSchema(username="john")

    def test_username_translated_errors(self, setup_i18n):
        """Should translate username errors."""
        set_locale('es')

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(username="ab")

        errors = BaseSchema.format_errors(exc_info.value)
        assert 'username' in errors
        # Spanish translation
        assert 'usuario' in errors['username'][0].lower()


# ============================================================================
# Test SlugValidatorMixin
# ============================================================================

class TestSlugValidator:
    """Test SlugValidatorMixin."""

    def test_slug_valid(self, setup_i18n):
        """Should accept valid slug."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        schema = ArticleSchema(slug="my-article-title")
        assert schema.slug == "my-article-title"

    def test_slug_lowercase_only(self, setup_i18n):
        """Should reject uppercase letters."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        with pytest.raises(ValidationError):
            ArticleSchema(slug="My-Article")

    def test_slug_no_spaces(self, setup_i18n):
        """Should reject spaces."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        with pytest.raises(ValidationError):
            ArticleSchema(slug="my article")

    def test_slug_no_special_chars(self, setup_i18n):
        """Should reject special characters."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        with pytest.raises(ValidationError):
            ArticleSchema(slug="my_article")

        with pytest.raises(ValidationError):
            ArticleSchema(slug="my@article")

        with pytest.raises(ValidationError):
            ArticleSchema(slug="my.article")

    def test_slug_no_consecutive_hyphens(self, setup_i18n):
        """Should reject consecutive hyphens."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        with pytest.raises(ValidationError):
            ArticleSchema(slug="my--article")

    def test_slug_no_start_end_hyphen(self, setup_i18n):
        """Should reject hyphen at start or end."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        # Start with hyphen
        with pytest.raises(ValidationError):
            ArticleSchema(slug="-my-article")

        # End with hyphen
        with pytest.raises(ValidationError):
            ArticleSchema(slug="my-article-")

    def test_slug_with_numbers(self, setup_i18n):
        """Should accept numbers."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        schema = ArticleSchema(slug="article-123")
        assert schema.slug == "article-123"

    def test_slug_single_word(self, setup_i18n):
        """Should accept single word."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        schema = ArticleSchema(slug="article")
        assert schema.slug == "article"

    def test_slug_only_numbers(self, setup_i18n):
        """Should accept only numbers."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        schema = ArticleSchema(slug="123")
        assert schema.slug == "123"


# ============================================================================
# Test Multiple Validators Combined
# ============================================================================

class TestCombinedValidators:
    """Test combining multiple validators."""

    def test_password_and_username_together(self, setup_i18n):
        """Should use multiple validators together."""

        class UserSchema(BaseSchema, PasswordValidatorMixin, UsernameValidatorMixin):
            username: str
            password: str

        schema = UserSchema(
            username="john_doe",
            password="Test1234!"
        )

        assert schema.username == "john_doe"
        assert schema.password == "Test1234!"

    def test_all_validators_together(self, setup_i18n):
        """Should combine all validators."""

        class ComplexSchema(
            BaseSchema,
            PasswordValidatorMixin,
            UsernameValidatorMixin,
            SlugValidatorMixin
        ):
            username: str
            password: str
            slug: str

        schema = ComplexSchema(
            username="john_doe",
            password="Test1234!",
            slug="my-article"
        )

        assert schema.username == "john_doe"
        assert schema.password == "Test1234!"
        assert schema.slug == "my-article"

    def test_multiple_validation_errors(self, setup_i18n):
        """Should report all validation errors."""

        class UserSchema(BaseSchema, PasswordValidatorMixin, UsernameValidatorMixin):
            username: str
            password: str

        with pytest.raises(ValidationError) as exc_info:
            UserSchema(
                username="ab",
                password="weak"
            )

        errors = BaseSchema.format_errors(exc_info.value)

        # Both fields should have errors
        assert 'username' in errors
        assert 'password' in errors


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_validation(self, setup_i18n):
        """Should handle empty strings."""

        class TestSchema(BaseSchema):
            name: str = min_length(1)

        with pytest.raises(ValidationError):
            TestSchema(name="")

    def test_whitespace_only_string(self, setup_i18n):
        """Should handle whitespace-only strings."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        with pytest.raises(ValidationError):
            UserSchema(username="   ")

    def test_unicode_in_password(self, setup_i18n):
        """Should handle Unicode characters."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        # Unicode special chars might not be recognized
        # Should still require ASCII special chars
        with pytest.raises(ValidationError):
            UserSchema(password="Test1234你好")

    def test_exact_boundary_values(self, setup_i18n):
        """Should handle exact boundary values."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        # Exactly min length
        schema = UserSchema(password="Test123!")
        assert len(schema.password) == 8

        # Exactly max length
        schema = UserSchema(password="Test1234567890!A")
        assert len(schema.password) == 16

    def test_none_value(self, setup_i18n):
        """Should handle None values."""

        class TestSchema(BaseSchema):
            name: str

        with pytest.raises(ValidationError):
            TestSchema(name=None)

    def test_numeric_string_in_username(self, setup_i18n):
        """Should handle numeric strings."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        # Cannot start with number
        with pytest.raises(ValidationError):
            UserSchema(username="123")

        # Can contain numbers
        schema = UserSchema(username="user123")
        assert schema.username == "user123"


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegration:
    """Test real-world integration scenarios."""

    def test_user_registration_schema(self, setup_i18n):
        """Should validate user registration."""

        class UserRegisterSchema(
            BaseSchema,
            PasswordValidatorMixin,
            UsernameValidatorMixin
        ):
            username: str
            email: EmailStr
            password: str
            age: int = min_value(18)

        # Valid registration
        schema = UserRegisterSchema(
            username="john_doe",
            email="john@example.com",
            password="Test1234!",
            age=25
        )

        assert schema.username == "john_doe"
        assert schema.email == "john@example.com"
        assert schema.password == "Test1234!"
        assert schema.age == 25

    def test_article_creation_schema(self, setup_i18n):
        """Should validate article creation."""

        class ArticleCreateSchema(BaseSchema, SlugValidatorMixin):
            title: str = length(5, 100)
            slug: str
            content: str = min_length(50)

        # Valid article
        schema = ArticleCreateSchema(
            title="My Great Article",
            slug="my-great-article",
            content="A" * 100
        )

        assert schema.title == "My Great Article"
        assert schema.slug == "my-great-article"

    def test_validation_with_api_response(self, setup_i18n):
        """Should format errors for API response."""

        class UserSchema(BaseSchema, PasswordValidatorMixin, UsernameValidatorMixin):
            username: str
            password: str

        try:
            UserSchema(
                username="ab",
                password="weak"
            )
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            # Should be ready for JSON response
            assert isinstance(errors, dict)

            # Each field should have list of strings
            for field, messages in errors.items():
                assert isinstance(messages, list)
                for msg in messages:
                    assert isinstance(msg, str)

    def test_multilingual_validation_errors(self, setup_i18n):
        """Should support multiple languages."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        # English errors
        set_locale('en')
        try:
            UserSchema(password="weak")
        except ValidationError as e:
            errors_en = BaseSchema.format_errors(e)
            assert 'password' in errors_en['password'][0].lower()

        # Spanish errors
        set_locale('es')
        try:
            UserSchema(password="weak")
        except ValidationError as e:
            errors_es = BaseSchema.format_errors(e)
            assert 'contraseña' in errors_es['password'][0].lower()
