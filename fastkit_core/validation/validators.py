"""Reusable validator mixins for complex validation rules."""

from pydantic import field_validator
import re
from fastkit_core.i18n import _


class PasswordValidatorMixin:
    PWD_MIN_LENGTH = 8
    PWD_MAX_LENGTH = 16
    VALIDATION_MSG_PWD_KEY_MIN_LENGTH = 'validation.password.min_length'
    VALIDATION_MSG_PWD_KEY_MAX_LENGTH = 'validation.password.max_length'
    VALIDATION_MSG_PWD_KEY_UPPERCASE = 'validation.password.uppercase'
    VALIDATION_MSG_PWD_KEY_SPECIAL_CHAR = 'validation.password.special_char'

    """
    Standard password validation mixin.

    Requirements:
    - 8-16 characters
    - At least one uppercase letter
    - At least one special character

    Usage:
        class UserCreate(BaseSchema, PasswordValidatorMixin):
            password: str
    """

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < cls.PWD_MIN_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_MIN_LENGTH, min=cls.PWD_MIN_LENGTH))

        if len(v) > cls.PWD_MAX_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_MAX_LENGTH, max=cls.PWD_MAX_LENGTH))

        if not re.search(r'[A-Z]', v):
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_UPPERCASE))

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_SPECIAL_CHAR))

        return v


class StrongPasswordValidatorMixin:
    PWD_MIN_LENGTH = 10
    PWD_MAX_LENGTH = 20
    VALIDATION_MSG_PWD_KEY_MIN_LENGTH = 'validation.password.min_length'
    VALIDATION_MSG_PWD_KEY_MAX_LENGTH = 'validation.password.max_length'
    VALIDATION_MSG_PWD_KEY_UPPERCASE = 'validation.password.uppercase'
    VALIDATION_MSG_PWD_KEY_SPECIAL_CHAR = 'validation.password.special_char'
    VALIDATION_MSG_PWD_KEY_LOWERCASE = 'validation.password.lowercase'
    VALIDATION_MSG_PWD_KEY_DIGIT = 'validation.password.digit'

    """
    Strong password validation mixin.

    Requirements:
    - 10-20 characters
    - Uppercase, lowercase, digit, special character
    """

    @field_validator('password')
    @classmethod
    def validate_strong_password(cls, v: str) -> str:
        if len(v) < cls.PWD_MIN_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_MIN_LENGTH, min=cls.PWD_MIN_LENGTH))

        if len(v) > cls.PWD_MAX_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_MAX_LENGTH, max=cls.PWD_MAX_LENGTH))

        if not re.search(r'[A-Z]', v):
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_UPPERCASE))

        if not re.search(r'[a-z]', v):
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_LOWERCASE))

        if not re.search(r'[0-9]', v):
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_DIGIT))

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError(_(cls.VALIDATION_MSG_PWD_KEY_SPECIAL_CHAR))

        return v


class UsernameValidatorMixin:
    USM_MIN_LENGTH = 3
    USM_MAX_LENGTH = 20
    VALIDATION_MSG_USM_KEY_MIN_LENGTH = 'validation.username.min_length'
    VALIDATION_MSG_USM_KEY_MAX_LENGTH = 'validation.username.max_length'
    VALIDATION_MSG_USM_KEY_FORMAT = 'validation.username.format'
    """
    Username validation mixin.

    Requirements:
    - 3-20 characters
    - Alphanumeric and underscore only
    - Cannot start with number
    """

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < cls.USM_MAX_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_USM_KEY_MIN_LENGTH, min=cls.USM_MIN_LENGTH))

        if len(v) > cls.USM_MAX_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_USM_KEY_MAX_LENGTH, max=cls.USM_MAX_LENGTH))

        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError(_(cls.VALIDATION_MSG_USM_KEY_FORMAT))

        return v


class SlugValidatorMixin:
    VALIDATION_MSG_SLUG_KEY_FORMAT = 'validation.slug.format'
    """
    Slug validation mixin.

    Requirements:
    - Lowercase letters, numbers, hyphens only
    - No consecutive hyphens
    - Cannot start/end with hyphen
    """

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError(_(cls.VALIDATION_MSG_SLUG_KEY_FORMAT))

        return v
