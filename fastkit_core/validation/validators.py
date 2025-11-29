"""Reusable validator mixins for complex validation rules."""

from pydantic import field_validator
import re
from fastkit_core.i18n import _


class PasswordValidatorMixin:

    MIN_LENGTH = 8
    MAX_LENGTH = 16
    VALIDATION_MSG_KEY_MIN_LENGTH = 'validation.password.min_length'
    VALIDATION_MSG_KEY_MAX_LENGTH = 'validation.password.max_length'
    VALIDATION_MSG_KEY_UPPERCASE = 'validation.password.uppercase'
    VALIDATION_MSG_KEY_SPECIAL_CHAR = 'validation.password.special_char'

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
        if len(v) < cls.MIN_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_KEY_MIN_LENGTH, min=cls.MIN_LENGTH))

        if len(v) > cls.MAX_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_KEY_MAX_LENGTH, max=cls.MAX_LENGTH))

        if not re.search(r'[A-Z]', v):
            raise ValueError(_(cls.VALIDATION_MSG_KEY_UPPERCASE))

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError(_(cls.VALIDATION_MSG_KEY_SPECIAL_CHAR))

        return v


class StrongPasswordValidatorMixin:
    MIN_LENGTH = 10
    MAX_LENGTH = 20
    VALIDATION_MSG_KEY_MIN_LENGTH = 'validation.password.min_length'
    VALIDATION_MSG_KEY_MAX_LENGTH = 'validation.password.max_length'
    VALIDATION_MSG_KEY_UPPERCASE = 'validation.password.uppercase'
    VALIDATION_MSG_KEY_SPECIAL_CHAR = 'validation.password.special_char'
    VALIDATION_MSG_KEY_LOWERCASE = 'validation.password.lowercase'
    VALIDATION_MSG_KEY_DIGIT = 'validation.password.digit'

    """
    Strong password validation mixin.

    Requirements:
    - 10-20 characters
    - Uppercase, lowercase, digit, special character
    """

    @field_validator('password')
    @classmethod
    def validate_strong_password(cls, v: str) -> str:
        if len(v) < cls.MIN_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_KEY_MIN_LENGTH, min=cls.MIN_LENGTH))

        if len(v) > cls.MAX_LENGTH:
            raise ValueError(_(cls.VALIDATION_MSG_KEY_MAX_LENGTH, max=cls.MAX_LENGTH))

        if not re.search(r'[A-Z]', v):
            raise ValueError(_(cls.VALIDATION_MSG_KEY_UPPERCASE))

        if not re.search(r'[a-z]', v):
            raise ValueError(_(cls.VALIDATION_MSG_KEY_LOWERCASE))

        if not re.search(r'[0-9]', v):
            raise ValueError(_(cls.VALIDATION_MSG_KEY_DIGIT))

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError(_(cls.VALIDATION_MSG_KEY_SPECIAL_CHAR))

        return v
