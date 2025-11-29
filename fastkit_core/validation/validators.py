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