from pydantic import BaseModel, ValidationError
from fastkit_core.i18n import _
from typing import List, Dict, ClassVar


class BaseSchema(BaseModel):
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

    @classmethod
    def format_errors(cls, errors: ValidationError) -> Dict[str, List[str]]:
        """Formatting validation messages: {"field": ["message"]}"""

        formatted_errors: Dict[str, List[str]] = {}
        for error in errors.errors():
            field_name = str(error['loc'][0])

            if field_name not in formatted_errors:
                formatted_errors[field_name] = []

            # Get error details
            error_type = error['type']
            error_msg = error['msg']
            error_ctx = error.get('ctx', {})

            # Translate message based on error type
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
        Translate a single error message.

        Args:
            error_type: Pydantic error type (e.g., 'string_too_short')
            field_name: Name of the field
            context: Error context with values (min_length, ge, etc.)
            default_msg: Default Pydantic message (fallback)

        Returns:
            Translated error message
        """

        # Special handling for value_error with custom message
        # When validators raise ValueError with custom message,
        # Pydantic wraps it as 'value_error' with the message in default_msg
        if error_type == 'value_error':
            # Check if message looks like it's from our custom validator
            # (already translated by the validator itself)
            # Pattern: "Value error, <actual message>"
            if default_msg.startswith('Value error, '):
                # Extract the actual message (already translated)
                return default_msg.replace('Value error, ', '')

            # If it's a generic value_error, try to translate
            # But if no translation exists, use the actual error message
            translation_key = 'validation.value_error'
            params = {'field': field_name, **context}
            translated = _(translation_key, **params)

            # If translation not found, use the actual error message
            if translated == translation_key:
                return default_msg.replace('Value error, ', '')

            return translated

        # Get translation key for other error types
        translation_key = cls.VALIDATION_MESSAGE_MAP.get(error_type, 'validation.value_error')

        # Prepare translation parameters
        params = {
            'field': field_name,
            **context  # Includes min_length, ge, le, etc.
        }

        # Translate
        translated = _(translation_key, **params)

        # If translation key not found, _() returns the key itself
        # In that case, use default Pydantic message
        if translated == translation_key:
            return default_msg

        return translated