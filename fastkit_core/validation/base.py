from __future__ import annotations

import json
from typing import Any, List, Dict, ClassVar

from pydantic import BaseModel, ValidationError, ConfigDict

from fastkit_core.i18n import _


class BaseSchema(BaseModel):
    """
    Base schema for all FastKit schemas.

    Provides:
    - ORM mode enabled by default (from_attributes=True)
    - Standardized error formatting with i18n support
    - to_dict() helper with exclude_none support
    - to_json_str() helper
    - config_exclude_none() and config_exclude_fields() class methods

    Example:
        class UserResponse(BaseSchema):
            id: int
            name: str
            # from_attributes=True is already set — no extra config needed

        # Works directly with SQLAlchemy ORM objects
        user_response = UserResponse.model_validate(user_orm_instance)

        # Computed fields
        from pydantic import computed_field

        class UserResponse(BaseSchema):
            first_name: str
            last_name: str

            @computed_field
            @property
            def full_name(self) -> str:
                return f"{self.first_name} {self.last_name}"
    """

    model_config = ConfigDict(from_attributes=True)

    # Pydantic error type → translation key mapping
    VALIDATION_MESSAGE_MAP: ClassVar[Dict[str, str]] = {
        'missing': 'validation.required',
        'string_too_short': 'validation.string_too_short',
        'string_too_long': 'validation.string_too_long',
        'value_error': 'validation.value_error',
        'value_error.email': 'validation.email',
        'value_error.url': 'validation.url',
        'greater_than_equal': 'validation.greater_than_equal',
        'less_than_equal': 'validation.less_than_equal',
        'greater_than': 'validation.greater_than',
        'less_than': 'validation.less_than',
        'string_pattern_mismatch': 'validation.string_pattern_mismatch',
    }

    # ========================================================================
    # Serialization Helpers
    # ========================================================================

    def to_dict(self, exclude_none: bool = False) -> Dict[str, Any]:
        """
        Convert schema to dictionary.

        Args:
            exclude_none: If True, fields with None values are excluded.

        Returns:
            Dictionary representation of the schema.

        Example:
            user = UserResponse(id=1, name="John", avatar=None)

            user.to_dict()
            # {'id': 1, 'name': 'John', 'avatar': None}

            user.to_dict(exclude_none=True)
            # {'id': 1, 'name': 'John'}
        """
        return self.model_dump(exclude_none=exclude_none)

    def to_json_str(self, exclude_none: bool = False) -> str:
        """
        Serialize schema to a JSON string.

        Args:
            exclude_none: If True, fields with None values are excluded.

        Returns:
            JSON string representation.

        Example:
            user = UserResponse(id=1, name="John")
            json_str = user.to_json_str()
            # '{"id": 1, "name": "John"}'
        """
        return self.model_dump_json(exclude_none=exclude_none)

    # ========================================================================
    # Config Helpers
    # ========================================================================

    @classmethod
    def config_exclude_none(cls) -> ConfigDict:
        """
        Return a ConfigDict that excludes None fields during serialization.

        Use this when you want a schema to always omit None values in its
        output without calling to_dict(exclude_none=True) every time.

        Example:
            class UserResponse(BaseSchema):
                id: int
                name: str
                avatar: str | None = None

                model_config = BaseSchema.config_exclude_none()

            UserResponse(id=1, name="John", avatar=None).model_dump()
            # {'id': 1, 'name': 'John'}
        """
        return ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def config_exclude_fields(cls, fields: list[str]) -> ConfigDict:
        """
        Return a ConfigDict that excludes specific fields during serialization.

        Note: Pydantic v2 handles field exclusion at the field level via
        Field(exclude=True). This helper documents the recommended pattern
        and returns a base ConfigDict. For per-field exclusion, use:

            field_name: type = Field(exclude=True)

        Example:
            class UserResponse(BaseSchema):
                id: int
                name: str
                internal_token: str = Field(exclude=True)

                model_config = BaseSchema.config_exclude_fields(['internal_token'])
        """
        return ConfigDict(from_attributes=True)

    # ========================================================================
    # Error Formatting
    # ========================================================================

    @classmethod
    def format_errors(cls, errors: ValidationError) -> Dict[str, List[str]]:
        """
        Format Pydantic validation errors into a structured dict.

        Returns:
            Dict mapping field names to lists of translated error messages.
            Example: {"email": ["The email field is required"]}
        """
        formatted_errors: Dict[str, List[str]] = {}

        for error in errors.errors():
            field_name = str(error['loc'][0])

            if field_name not in formatted_errors:
                formatted_errors[field_name] = []

            error_type = error['type']
            error_msg = error['msg']
            error_ctx = error.get('ctx', {})

            translated_msg = cls._translate_error(
                error_type=error_type,
                field_name=field_name,
                context=error_ctx,
                default_msg=error_msg
            )

            formatted_errors[field_name].append(translated_msg)

        return formatted_errors

    @classmethod
    def _translate_error(
            cls,
            error_type: str,
            field_name: str,
            context: dict,
            default_msg: str
    ) -> str:
        """
        Translate a single Pydantic error message using i18n keys.

        Falls back to the original Pydantic message when no translation
        is found for the given error type.
        """
        if error_type == 'value_error':
            if default_msg.startswith('Value error, '):
                return default_msg.replace('Value error, ', '')

            translation_key = 'validation.value_error'
            params = {'field': field_name, **context}
            translated = _(translation_key, **params)

            if translated == translation_key:
                return default_msg.replace('Value error, ', '')

            return translated

        translation_key = cls.VALIDATION_MESSAGE_MAP.get(error_type, 'validation.value_error')
        params = {'field': field_name, **context}
        translated = _(translation_key, **params)

        if translated == translation_key:
            return default_msg

        return translated


class BaseCreateSchema(BaseSchema):
    """
    Base schema for create operations.

    Conventions:
    - Extra fields are forbidden (prevents accidental mass assignment)
    - Whitespace is stripped from string fields via validators in subclasses
    - from_attributes=True inherited from BaseSchema

    Example:
        class UserCreate(BaseCreateSchema):
            name: str
            email: str

        # Extra fields raise a validation error
        UserCreate(name="John", email="j@example.com", role="admin")
        # ValidationError: extra fields not permitted
    """

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class BaseUpdateSchema(BaseSchema):
    """
    Base schema for partial update operations.

    Conventions:
    - All fields are optional by convention (partial update / PATCH pattern)
    - Extra fields are forbidden
    - from_attributes=True inherited from BaseSchema

    Subclasses should declare all fields with a default of None:

        class UserUpdate(BaseUpdateSchema):
            name: str | None = None
            email: str | None = None

    This ensures that only explicitly provided fields are included when
    converting to a dict with model_dump(exclude_unset=True), which is
    what BaseCrudService._to_dict() does internally.

    Example:
        data = UserUpdate(name="Jane")
        data.model_dump(exclude_unset=True)
        # {'name': 'Jane'}   ← email not included because it was not set
    """

    model_config = ConfigDict(from_attributes=True, extra='forbid')
