"""
Comprehensive tests for FastKit Core Validation module.

Tests BaseSchema, BaseCreateSchema, BaseUpdateSchema, validation rules,
and validator mixins:
- BaseSchema — ORM mode, serialization helpers, config helpers, error formatting
- BaseCreateSchema — extra fields forbidden, inheritance
- BaseUpdateSchema — extra fields forbidden, partial update convention
- Computed fields pattern
- Validation rules (min_length, max_length, etc.)
- PasswordValidatorMixin
- StrongPasswordValidatorMixin
- UsernameValidatorMixin
- SlugValidatorMixin

Target Coverage: 95%+
"""

import json
from typing import Any, ClassVar, Dict

import pytest
from pydantic import Field, ValidationError, EmailStr, computed_field

from fastkit_core.config import ConfigManager, set_config_manager
from fastkit_core.i18n import TranslationManager, set_locale, set_translation_manager
from fastkit_core.validation import (
    BaseSchema,
    BaseCreateSchema,
    BaseUpdateSchema,
    between,
    format_validation_errors,
    length,
    max_length,
    max_value,
    min_length,
    min_value,
    PasswordValidatorMixin,
    pattern,
    raise_multiple_validation_errors,
    raise_validation_error,
    SlugValidatorMixin,
    StrongPasswordValidatorMixin,
    UsernameValidatorMixin,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def translations_dir(tmp_path):
    """Create temporary translations directory with validation messages."""
    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()

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
                "special_char": "Password must contain at least one special character",
            },
            "username": {
                "min_length": "Username must be at least {min} characters",
                "max_length": "Username must not exceed {max} characters",
                "format": "Username must start with a letter and contain only letters, numbers, and underscores",
            },
            "slug": {
                "format": "Slug must be lowercase letters, numbers, and hyphens only",
            },
        }
    }

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
                "special_char": "La contraseña debe contener al menos un carácter especial",
            },
            "username": {
                "min_length": "El nombre de usuario debe tener al menos {min} caracteres",
                "format": "El nombre de usuario debe comenzar con una letra y contener solo letras, números y guiones bajos",
            },
        }
    }

    with open(trans_dir / "en.json", "w", encoding="utf-8") as f:
        json.dump(en_content, f, ensure_ascii=False, indent=2)

    with open(trans_dir / "es.json", "w", encoding="utf-8") as f:
        json.dump(es_content, f, ensure_ascii=False, indent=2)

    return trans_dir


@pytest.fixture
def setup_i18n(translations_dir):
    """Setup i18n with translations."""
    config = ConfigManager(modules=[], auto_load=False)
    config.load()
    config.set('app.TRANSLATIONS_PATH', str(translations_dir))
    config.set('app.DEFAULT_LANGUAGE', 'en')
    config.set('app.FALLBACK_LANGUAGE', 'en')
    set_config_manager(config)

    manager = TranslationManager(translations_dir=translations_dir)
    set_translation_manager(manager)
    set_locale('en')

    yield

    set_locale('en')


# ============================================================================
# Test BaseSchema — ORM Mode
# ============================================================================

class TestBaseSchemaOrmMode:
    """Test that BaseSchema has from_attributes=True enabled by default."""

    def test_from_attributes_is_true(self):
        """model_config should have from_attributes=True."""
        assert BaseSchema.model_config.get('from_attributes') is True

    def test_subclass_inherits_from_attributes(self):
        """Subclasses should inherit ORM mode without re-declaring it."""

        class UserResponse(BaseSchema):
            id: int
            name: str

        assert UserResponse.model_config.get('from_attributes') is True

    def test_model_validate_from_orm_object(self):
        """Should accept objects with attribute access (ORM-like)."""

        class UserResponse(BaseSchema):
            id: int
            name: str

        class FakeOrmUser:
            def __init__(self):
                self.id = 1
                self.name = "Alice"

        result = UserResponse.model_validate(FakeOrmUser())
        assert result.id == 1
        assert result.name == "Alice"

    def test_model_validate_from_dict_still_works(self):
        """Should still accept plain dicts after enabling from_attributes."""

        class UserResponse(BaseSchema):
            id: int
            name: str

        result = UserResponse.model_validate({"id": 2, "name": "Bob"})
        assert result.id == 2
        assert result.name == "Bob"

    def test_subclass_can_override_model_config(self):
        """Subclass should be able to override or extend model_config."""
        from pydantic import ConfigDict

        class StrictSchema(BaseSchema):
            value: int
            model_config = ConfigDict(from_attributes=True, extra='forbid')

        with pytest.raises(ValidationError):
            StrictSchema(value=1, unexpected_field="oops")


# ============================================================================
# Test BaseSchema — Serialization Helpers
# ============================================================================

class TestBaseSchemaToDict:
    """Test BaseSchema.to_dict() helper."""

    def test_to_dict_returns_all_fields(self):
        """Should return all fields including None values by default."""

        class Schema(BaseSchema):
            id: int
            name: str
            avatar: str | None = None

        instance = Schema(id=1, name="John", avatar=None)
        result = instance.to_dict()

        assert result == {"id": 1, "name": "John", "avatar": None}

    def test_to_dict_exclude_none_false_by_default(self):
        """Default exclude_none=False should keep None values."""

        class Schema(BaseSchema):
            name: str
            bio: str | None = None

        instance = Schema(name="Alice", bio=None)
        result = instance.to_dict()

        assert "bio" in result
        assert result["bio"] is None

    def test_to_dict_exclude_none_true(self):
        """exclude_none=True should drop None fields."""

        class Schema(BaseSchema):
            id: int
            name: str
            bio: str | None = None
            avatar: str | None = None

        instance = Schema(id=1, name="Alice", bio=None, avatar=None)
        result = instance.to_dict(exclude_none=True)

        assert result == {"id": 1, "name": "Alice"}
        assert "bio" not in result
        assert "avatar" not in result

    def test_to_dict_exclude_none_keeps_non_none_optionals(self):
        """exclude_none=True should keep optional fields that have a value."""

        class Schema(BaseSchema):
            name: str
            bio: str | None = None

        instance = Schema(name="Bob", bio="Developer")
        result = instance.to_dict(exclude_none=True)

        assert result == {"name": "Bob", "bio": "Developer"}

    def test_to_dict_returns_dict_type(self):
        """to_dict() should always return a plain dict."""

        class Schema(BaseSchema):
            value: int

        instance = Schema(value=42)
        assert isinstance(instance.to_dict(), dict)

    def test_to_dict_with_nested_schema(self):
        """Should serialize nested schemas."""

        class AddressSchema(BaseSchema):
            city: str

        class UserSchema(BaseSchema):
            name: str
            address: AddressSchema

        instance = UserSchema(name="Alice", address=AddressSchema(city="Belgrade"))
        result = instance.to_dict()

        assert result["name"] == "Alice"
        assert result["address"] == {"city": "Belgrade"}


class TestBaseSchemaToJsonStr:
    """Test BaseSchema.to_json_str() helper."""

    def test_to_json_str_returns_string(self):
        """Should return a string."""

        class Schema(BaseSchema):
            id: int
            name: str

        instance = Schema(id=1, name="John")
        result = instance.to_json_str()

        assert isinstance(result, str)

    def test_to_json_str_is_valid_json(self):
        """Output should be parseable JSON."""

        class Schema(BaseSchema):
            id: int
            name: str

        instance = Schema(id=1, name="John")
        parsed = json.loads(instance.to_json_str())

        assert parsed == {"id": 1, "name": "John"}

    def test_to_json_str_includes_none_by_default(self):
        """Should include None fields by default."""

        class Schema(BaseSchema):
            name: str
            bio: str | None = None

        instance = Schema(name="Alice", bio=None)
        parsed = json.loads(instance.to_json_str())

        assert "bio" in parsed
        assert parsed["bio"] is None

    def test_to_json_str_exclude_none(self):
        """exclude_none=True should omit None fields from JSON."""

        class Schema(BaseSchema):
            name: str
            bio: str | None = None

        instance = Schema(name="Alice", bio=None)
        parsed = json.loads(instance.to_json_str(exclude_none=True))

        assert "bio" not in parsed
        assert parsed == {"name": "Alice"}

    def test_to_json_str_consistent_with_to_dict(self):
        """to_json_str() result should match json.dumps(to_dict())."""

        class Schema(BaseSchema):
            id: int
            name: str
            value: float | None = None

        instance = Schema(id=1, name="Test", value=None)

        from_str = json.loads(instance.to_json_str(exclude_none=True))
        from_dict = instance.to_dict(exclude_none=True)

        assert from_str == from_dict


# ============================================================================
# Test BaseSchema — Config Helpers
# ============================================================================

class TestBaseSchemaConfigHelpers:
    """Test config_exclude_none() and config_exclude_fields() helpers."""

    def test_config_exclude_none_returns_config_dict(self):
        """config_exclude_none() should return a ConfigDict."""
        from pydantic import ConfigDict
        result = BaseSchema.config_exclude_none()
        assert isinstance(result, dict)

    def test_config_exclude_none_has_from_attributes(self):
        """Returned ConfigDict should still have from_attributes=True."""
        result = BaseSchema.config_exclude_none()
        assert result.get('from_attributes') is True

    def test_config_exclude_fields_returns_config_dict(self):
        """config_exclude_fields() should return a ConfigDict."""
        result = BaseSchema.config_exclude_fields(['secret'])
        assert isinstance(result, dict)

    def test_config_exclude_fields_has_from_attributes(self):
        """Returned ConfigDict should still have from_attributes=True."""
        result = BaseSchema.config_exclude_fields(['secret'])
        assert result.get('from_attributes') is True

    def test_field_exclude_true_works(self):
        """Field(exclude=True) should exclude a field from serialization."""

        class UserResponse(BaseSchema):
            id: int
            name: str
            internal_token: str = Field(exclude=True)

        instance = UserResponse(id=1, name="Alice", internal_token="secret")
        data = instance.to_dict()

        assert "internal_token" not in data
        assert data == {"id": 1, "name": "Alice"}


# ============================================================================
# Test BaseSchema — Computed Fields
# ============================================================================

class TestBaseSchemaComputedFields:
    """Test the computed_field pattern on BaseSchema subclasses."""

    def test_computed_field_basic(self):
        """@computed_field should add a derived property to the schema."""

        class UserResponse(BaseSchema):
            first_name: str
            last_name: str

            @computed_field
            @property
            def full_name(self) -> str:
                return f"{self.first_name} {self.last_name}"

        user = UserResponse(first_name="John", last_name="Doe")
        assert user.full_name == "John Doe"

    def test_computed_field_included_in_to_dict(self):
        """Computed fields should appear in to_dict() output."""

        class UserResponse(BaseSchema):
            first_name: str
            last_name: str

            @computed_field
            @property
            def full_name(self) -> str:
                return f"{self.first_name} {self.last_name}"

        user = UserResponse(first_name="Jane", last_name="Smith")
        data = user.to_dict()

        assert "full_name" in data
        assert data["full_name"] == "Jane Smith"

    def test_computed_field_included_in_to_json_str(self):
        """Computed fields should appear in to_json_str() output."""

        class UserResponse(BaseSchema):
            first_name: str
            last_name: str

            @computed_field
            @property
            def full_name(self) -> str:
                return f"{self.first_name} {self.last_name}"

        user = UserResponse(first_name="Alice", last_name="Wonder")
        parsed = json.loads(user.to_json_str())

        assert parsed["full_name"] == "Alice Wonder"

    def test_computed_field_with_none_handling(self):
        """Computed fields should handle optional source fields correctly."""

        class UserResponse(BaseSchema):
            avatar_path: str | None = None

            @computed_field
            @property
            def avatar_url(self) -> str | None:
                if not self.avatar_path:
                    return None
                return f"/storage/{self.avatar_path}"

        user_with_avatar = UserResponse(avatar_path="photo.jpg")
        user_without_avatar = UserResponse(avatar_path=None)

        assert user_with_avatar.avatar_url == "/storage/photo.jpg"
        assert user_without_avatar.avatar_url is None

    def test_computed_field_with_orm_object(self):
        """Computed fields should work when schema is built from an ORM object."""

        class UserResponse(BaseSchema):
            first_name: str
            last_name: str

            @computed_field
            @property
            def full_name(self) -> str:
                return f"{self.first_name} {self.last_name}"

        class FakeOrmUser:
            first_name = "Maria"
            last_name = "Garcia"

        user = UserResponse.model_validate(FakeOrmUser())
        assert user.full_name == "Maria Garcia"

    def test_multiple_computed_fields(self):
        """Multiple computed fields should all work independently."""

        class ProductResponse(BaseSchema):
            price: float
            tax_rate: float = 0.20

            @computed_field
            @property
            def tax_amount(self) -> float:
                return round(self.price * self.tax_rate, 2)

            @computed_field
            @property
            def total_price(self) -> float:
                return round(self.price + self.tax_amount, 2)

        product = ProductResponse(price=100.0)
        assert product.tax_amount == 20.0
        assert product.total_price == 120.0

        data = product.to_dict()
        assert data["tax_amount"] == 20.0
        assert data["total_price"] == 120.0


# ============================================================================
# Test BaseCreateSchema
# ============================================================================

class TestBaseCreateSchema:
    """Test BaseCreateSchema conventions."""

    def test_from_attributes_inherited(self):
        """Should inherit from_attributes=True from BaseSchema."""
        assert BaseCreateSchema.model_config.get('from_attributes') is True

    def test_extra_fields_forbidden(self):
        """Should raise ValidationError when extra fields are provided."""

        class UserCreate(BaseCreateSchema):
            name: str
            email: str

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(name="John", email="j@example.com", role="admin")

        errors = exc_info.value.errors()
        assert any(e['type'] == 'extra_forbidden' for e in errors)

    def test_valid_fields_pass(self):
        """Should accept valid data without extra fields."""

        class UserCreate(BaseCreateSchema):
            name: str
            email: str

        schema = UserCreate(name="John", email="j@example.com")
        assert schema.name == "John"
        assert schema.email == "j@example.com"

    def test_is_subclass_of_base_schema(self):
        """BaseCreateSchema should be a subclass of BaseSchema."""
        assert issubclass(BaseCreateSchema, BaseSchema)

    def test_inherits_to_dict(self):
        """Should inherit to_dict() helper from BaseSchema."""

        class UserCreate(BaseCreateSchema):
            name: str
            bio: str | None = None

        instance = UserCreate(name="Alice", bio=None)
        result = instance.to_dict(exclude_none=True)

        assert result == {"name": "Alice"}

    def test_inherits_format_errors(self):
        """Should inherit format_errors() from BaseSchema."""

        class UserCreate(BaseCreateSchema):
            name: str

        with pytest.raises(ValidationError) as exc_info:
            UserCreate()

        errors = BaseCreateSchema.format_errors(exc_info.value)
        assert "name" in errors

    def test_multiple_extra_fields_all_reported(self):
        """All extra fields should be reported in the error."""

        class UserCreate(BaseCreateSchema):
            name: str

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(name="John", role="admin", is_superuser=True)

        error_fields = [e['loc'][-1] for e in exc_info.value.errors()]
        assert 'role' in error_fields
        assert 'is_superuser' in error_fields

    def test_with_validators(self, setup_i18n):
        """Should work with validator mixins."""

        class UserCreate(BaseCreateSchema, PasswordValidatorMixin):
            email: str
            password: str

        schema = UserCreate(email="j@example.com", password="Test123!")
        assert schema.password == "Test123!"

        with pytest.raises(ValidationError):
            UserCreate(email="j@example.com", password="weak", extra_field="x")


# ============================================================================
# Test BaseUpdateSchema
# ============================================================================

class TestBaseUpdateSchema:
    """Test BaseUpdateSchema conventions."""

    def test_from_attributes_inherited(self):
        """Should inherit from_attributes=True from BaseSchema."""
        assert BaseUpdateSchema.model_config.get('from_attributes') is True

    def test_extra_fields_forbidden(self):
        """Should raise ValidationError when extra fields are provided."""

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            email: str | None = None

        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(name="Jane", role="admin")

        errors = exc_info.value.errors()
        assert any(e['type'] == 'extra_forbidden' for e in errors)

    def test_all_fields_optional_by_convention(self):
        """Should accept empty instantiation when all fields are optional."""

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            email: str | None = None
            age: int | None = None

        # Empty update is valid
        schema = UserUpdate()
        assert schema.name is None
        assert schema.email is None
        assert schema.age is None

    def test_partial_update_only_set_fields(self):
        """model_dump(exclude_unset=True) should only include explicitly set fields."""

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            email: str | None = None
            age: int | None = None

        update = UserUpdate(name="Jane")
        data = update.model_dump(exclude_unset=True)

        assert data == {"name": "Jane"}
        assert "email" not in data
        assert "age" not in data

    def test_partial_update_multiple_fields(self):
        """Multiple set fields should all appear in exclude_unset dump."""

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            email: str | None = None
            age: int | None = None

        update = UserUpdate(name="Jane", age=30)
        data = update.model_dump(exclude_unset=True)

        assert data == {"name": "Jane", "age": 30}
        assert "email" not in data

    def test_is_subclass_of_base_schema(self):
        """BaseUpdateSchema should be a subclass of BaseSchema."""
        assert issubclass(BaseUpdateSchema, BaseSchema)

    def test_inherits_to_dict(self):
        """Should inherit to_dict() helper from BaseSchema."""

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            bio: str | None = None

        instance = UserUpdate(name="Bob")
        result = instance.to_dict(exclude_none=True)

        assert result == {"name": "Bob"}

    def test_explicit_none_is_set(self):
        """Explicitly setting a field to None should include it in exclude_unset dump."""

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            bio: str | None = None

        # Explicitly passing None — developer wants to clear the field
        update = UserUpdate(bio=None)
        data = update.model_dump(exclude_unset=True)

        assert "bio" in data
        assert data["bio"] is None
        assert "name" not in data

    def test_with_to_dict_service_integration(self):
        """
        to_dict() should match what BaseCrudService._to_dict() produces,
        since it uses model_dump(exclude_unset=True) internally.
        """

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            email: str | None = None

        update = UserUpdate(name="Alice")

        # Simulate what _to_dict does
        service_dict = update.model_dump(exclude_unset=True)

        assert service_dict == {"name": "Alice"}


# ============================================================================
# Test BaseSchema — Error Translation (existing tests, unchanged)
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
            value: int

        try:
            TestSchema(value="not_a_number")
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert 'value' in errors
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

        schema = TestSchema(name="hello")
        assert schema.name == "hello"

        with pytest.raises(ValidationError):
            TestSchema(name="hi")

    def test_max_length_rule(self, setup_i18n):
        """Should validate maximum length."""

        class TestSchema(BaseSchema):
            name: str = max_length(10)

        schema = TestSchema(name="hello")
        assert schema.name == "hello"

        with pytest.raises(ValidationError):
            TestSchema(name="a" * 20)

    def test_length_range_rule(self, setup_i18n):
        """Should validate length range."""

        class TestSchema(BaseSchema):
            name: str = length(3, 10)

        schema = TestSchema(name="hello")
        assert schema.name == "hello"

        with pytest.raises(ValidationError):
            TestSchema(name="ab")

        with pytest.raises(ValidationError):
            TestSchema(name="a" * 20)

    def test_min_value_rule(self, setup_i18n):
        """Should validate minimum value."""

        class TestSchema(BaseSchema):
            age: int = min_value(18)

        schema = TestSchema(age=25)
        assert schema.age == 25

        with pytest.raises(ValidationError):
            TestSchema(age=15)

    def test_max_value_rule(self, setup_i18n):
        """Should validate maximum value."""

        class TestSchema(BaseSchema):
            score: int = max_value(100)

        schema = TestSchema(score=95)
        assert schema.score == 95

        with pytest.raises(ValidationError):
            TestSchema(score=150)

    def test_between_rule(self, setup_i18n):
        """Should validate value range."""

        class TestSchema(BaseSchema):
            age: int = between(18, 100)

        schema = TestSchema(age=25)
        assert schema.age == 25

        with pytest.raises(ValidationError):
            TestSchema(age=15)

        with pytest.raises(ValidationError):
            TestSchema(age=150)

    def test_pattern_rule(self, setup_i18n):
        """Should validate regex pattern."""

        class TestSchema(BaseSchema):
            code: str = pattern(r'^[A-Z]{3}\d{3}$')

        schema = TestSchema(code="ABC123")
        assert schema.code == "ABC123"

        with pytest.raises(ValidationError):
            TestSchema(code="abc123")

        with pytest.raises(ValidationError):
            TestSchema(code="ABCD1234")

    def test_float_between_rule(self, setup_i18n):
        """Should validate float ranges."""

        class TestSchema(BaseSchema):
            rating: float = between(0.0, 5.0)

        schema = TestSchema(rating=4.5)
        assert schema.rating == 4.5

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

        for char in '!@#$%^&*(),.?":{}|<>':
            schema = UserSchema(password=f"Test123{char}")
            assert schema.password == f"Test123{char}"

    def test_password_custom_length(self, setup_i18n):
        """Should allow custom length requirements."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            PWD_MIN_LENGTH: ClassVar[int] = 6
            PWD_MAX_LENGTH: ClassVar[int] = 10
            password: str

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
        with pytest.raises(ValidationError):

            class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
                password: str

            UserSchema(password="test12345!")

    def test_strong_password_lowercase_required(self, setup_i18n):
        with pytest.raises(ValidationError):

            class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
                password: str

            UserSchema(password="TEST12345!")

    def test_strong_password_digit_required(self, setup_i18n):
        with pytest.raises(ValidationError):

            class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
                password: str

            UserSchema(password="TestPassword!")

    def test_strong_password_special_required(self, setup_i18n):
        with pytest.raises(ValidationError):

            class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
                password: str

            UserSchema(password="Test1234567")

    def test_strong_password_all_requirements(self, setup_i18n):
        """Should enforce all requirements together."""

        class UserSchema(BaseSchema, StrongPasswordValidatorMixin):
            password: str

        for invalid in ["test12345!", "TEST12345!", "TestTest!!", "Test123456"]:
            with pytest.raises(ValidationError):
                UserSchema(password=invalid)

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

        with pytest.raises(ValidationError):
            UserSchema(username="123john")

        with pytest.raises(ValidationError):
            UserSchema(username="_john")

    def test_username_alphanumeric_underscore_only(self, setup_i18n):
        """Should allow only alphanumeric and underscore."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        schema = UserSchema(username="john_doe_123")
        assert schema.username == "john_doe_123"

        for invalid in ["john-doe", "john@doe", "john doe"]:
            with pytest.raises(ValidationError):
                UserSchema(username=invalid)

    def test_username_case_insensitive(self, setup_i18n):
        """Should accept both cases."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            username: str

        assert UserSchema(username="JohnDoe").username == "JohnDoe"
        assert UserSchema(username="johndoe").username == "johndoe"

    def test_username_custom_length(self, setup_i18n):
        """Should allow custom length requirements."""

        class UserSchema(BaseSchema, UsernameValidatorMixin):
            USM_MIN_LENGTH: ClassVar[int] = 5
            USM_MAX_LENGTH: ClassVar[int] = 15
            username: str

        schema = UserSchema(username="johndoe")
        assert schema.username == "johndoe"

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

        for invalid in ["my_article", "my@article", "my.article"]:
            with pytest.raises(ValidationError):
                ArticleSchema(slug=invalid)

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

        with pytest.raises(ValidationError):
            ArticleSchema(slug="-my-article")

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

        assert ArticleSchema(slug="article").slug == "article"

    def test_slug_only_numbers(self, setup_i18n):
        """Should accept only numbers."""

        class ArticleSchema(BaseSchema, SlugValidatorMixin):
            slug: str

        assert ArticleSchema(slug="123").slug == "123"


# ============================================================================
# Test Combined Validators
# ============================================================================

class TestCombinedValidators:
    """Test combining multiple validators."""

    def test_password_and_username_together(self, setup_i18n):
        """Should use multiple validators together."""

        class UserSchema(BaseSchema, PasswordValidatorMixin, UsernameValidatorMixin):
            username: str
            password: str

        schema = UserSchema(username="john_doe", password="Test1234!")
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
            UserSchema(username="ab", password="weak")

        errors = BaseSchema.format_errors(exc_info.value)
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

    def test_exact_boundary_values(self, setup_i18n):
        """Should handle exact boundary values."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        schema = UserSchema(password="Test123!")
        assert len(schema.password) == 8

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

        with pytest.raises(ValidationError):
            UserSchema(username="123")

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

        schema = ArticleCreateSchema(
            title="My Great Article",
            slug="my-great-article",
            content="A" * 100
        )
        assert schema.title == "My Great Article"
        assert schema.slug == "my-great-article"

    def test_create_and_update_schema_together(self, setup_i18n):
        """BaseCreateSchema and BaseUpdateSchema should work together in a typical CRUD flow."""

        class UserCreate(BaseCreateSchema):
            name: str
            email: str
            status: str = "active"

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            email: str | None = None
            status: str | None = None

        # Create
        create_data = UserCreate(name="John", email="j@example.com")
        assert create_data.name == "John"
        assert create_data.status == "active"

        # Partial update — only name
        update_data = UserUpdate(name="Jane")
        service_dict = update_data.model_dump(exclude_unset=True)
        assert service_dict == {"name": "Jane"}

        # Extra field on create — forbidden
        with pytest.raises(ValidationError):
            UserCreate(name="John", email="j@example.com", role="admin")

        # Extra field on update — forbidden
        with pytest.raises(ValidationError):
            UserUpdate(name="Jane", role="admin")

    def test_validation_with_api_response(self, setup_i18n):
        """Should format errors for API response."""

        class UserSchema(BaseSchema, PasswordValidatorMixin, UsernameValidatorMixin):
            username: str
            password: str

        try:
            UserSchema(username="ab", password="weak")
        except ValidationError as e:
            errors = BaseSchema.format_errors(e)

            assert isinstance(errors, dict)
            for field, messages in errors.items():
                assert isinstance(messages, list)
                for msg in messages:
                    assert isinstance(msg, str)

    def test_multilingual_validation_errors(self, setup_i18n):
        """Should support multiple languages."""

        class UserSchema(BaseSchema, PasswordValidatorMixin):
            password: str

        set_locale('en')
        try:
            UserSchema(password="weak")
        except ValidationError as e:
            errors_en = BaseSchema.format_errors(e)
            assert 'password' in errors_en['password'][0].lower()

        set_locale('es')
        try:
            UserSchema(password="weak")
        except ValidationError as e:
            errors_es = BaseSchema.format_errors(e)
            assert 'contraseña' in errors_es['password'][0].lower()

    def test_orm_mode_with_create_and_update_schemas(self):
        """BaseCreateSchema and BaseUpdateSchema should support ORM objects."""

        class UserCreate(BaseCreateSchema):
            name: str
            email: str

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None

        class FakeOrm:
            name = "Alice"
            email = "a@example.com"

        result = UserCreate.model_validate(FakeOrm())
        assert result.name == "Alice"


# ============================================================================
# Test Error Helper Functions (unchanged)
# ============================================================================

class TestRaiseValidationError:
    """Test raise_validation_error helper."""

    def test_raises_validation_error(self):
        """Should raise ValidationError with correct field and message."""
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error('email', 'Email already exists')

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('email',)
        assert 'Email already exists' in errors[0]['msg']

    def test_raises_with_value(self):
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error('email', 'Email already exists', 'test@test.com')

        errors = exc_info.value.errors()
        assert errors[0]['input'] == 'test@test.com'

    def test_raises_with_none_value(self):
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error('name', 'Name is required', None)

        errors = exc_info.value.errors()
        assert errors[0]['input'] is None

    def test_error_type_is_value_error(self):
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error('field', 'some error')

        errors = exc_info.value.errors()
        assert errors[0]['type'] == 'value_error'

    def test_format_errors_integration(self, setup_i18n):
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error('username', 'Username taken', 'john')

        formatted = format_validation_errors(exc_info.value.errors())
        assert 'username' in formatted
        assert any('Username taken' in msg for msg in formatted['username'])


class TestRaiseMultipleValidationErrors:
    """Test raise_multiple_validation_errors helper."""

    def test_raises_multiple_errors(self):
        with pytest.raises(ValidationError) as exc_info:
            raise_multiple_validation_errors([
                ('email', 'Email is required', None),
                ('password', 'Password is too short', 'abc'),
            ])

        errors = exc_info.value.errors()
        assert len(errors) == 2
        fields = [e['loc'][0] for e in errors]
        assert 'email' in fields
        assert 'password' in fields

    def test_raises_multiple_errors_same_field(self):
        with pytest.raises(ValidationError) as exc_info:
            raise_multiple_validation_errors([
                ('password', 'Too short', 'ab'),
                ('password', 'Must contain uppercase', 'ab'),
            ])

        errors = exc_info.value.errors()
        assert len(errors) == 2
        assert all(e['loc'] == ('password',) for e in errors)

    def test_raises_single_error_in_list(self):
        with pytest.raises(ValidationError) as exc_info:
            raise_multiple_validation_errors([('name', 'Name is required', None)])

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('name',)

    def test_preserves_input_values(self):
        with pytest.raises(ValidationError) as exc_info:
            raise_multiple_validation_errors([
                ('email', 'Invalid email', 'bad-email'),
                ('age', 'Must be 18+', 15),
            ])

        errors = exc_info.value.errors()
        inputs = {e['loc'][0]: e['input'] for e in errors}
        assert inputs['email'] == 'bad-email'
        assert inputs['age'] == 15

    def test_format_errors_integration(self, setup_i18n):
        with pytest.raises(ValidationError) as exc_info:
            raise_multiple_validation_errors([
                ('email', 'Email is required', None),
                ('password', 'Password too short', 'abc'),
                ('password', 'Must contain digit', 'abc'),
            ])

        formatted = format_validation_errors(exc_info.value.errors())
        assert 'email' in formatted
        assert 'password' in formatted
        assert len(formatted['password']) == 2


class TestFormatValidationErrors:
    """Test format_validation_errors helper."""

    def test_formats_single_error(self):
        raw_errors = [{'loc': ('name',), 'msg': 'Field required', 'type': 'missing'}]
        result = format_validation_errors(raw_errors)
        assert result == {'name': ['Field required']}

    def test_formats_multiple_fields(self):
        raw_errors = [
            {'loc': ('name',), 'msg': 'Field required', 'type': 'missing'},
            {'loc': ('email',), 'msg': 'Invalid email', 'type': 'value_error'},
        ]
        result = format_validation_errors(raw_errors)
        assert result['name'] == ['Field required']
        assert result['email'] == ['Invalid email']

    def test_formats_multiple_errors_same_field(self):
        raw_errors = [
            {'loc': ('password',), 'msg': 'Too short', 'type': 'value_error'},
            {'loc': ('password',), 'msg': 'Needs uppercase', 'type': 'value_error'},
        ]
        result = format_validation_errors(raw_errors)
        assert len(result['password']) == 2
        assert 'Too short' in result['password']
        assert 'Needs uppercase' in result['password']

    def test_formats_nested_loc(self):
        raw_errors = [
            {'loc': ('body', 'address', 'city'), 'msg': 'Field required', 'type': 'missing'},
        ]
        result = format_validation_errors(raw_errors)
        assert 'city' in result
        assert result['city'] == ['Field required']

    def test_handles_empty_loc(self):
        raw_errors = [{'loc': (), 'msg': 'Something went wrong', 'type': 'value_error'}]
        result = format_validation_errors(raw_errors)
        assert 'unknown' in result

    def test_handles_missing_loc(self):
        raw_errors = [{'msg': 'Something went wrong', 'type': 'value_error'}]
        result = format_validation_errors(raw_errors)
        assert 'unknown' in result

    def test_empty_error_list(self):
        assert format_validation_errors([]) == {}

    def test_with_real_pydantic_errors(self, setup_i18n):
        class TestSchema(BaseSchema):
            name: str
            email: str = Field(min_length=5)

        with pytest.raises(ValidationError) as exc_info:
            TestSchema(email="ab")

        result = format_validation_errors(exc_info.value.errors())
        assert 'name' in result
        assert 'email' in result
        assert len(result['name']) >= 1
        assert len(result['email']) >= 1
