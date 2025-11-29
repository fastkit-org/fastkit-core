from pydantic import BaseModel, ValidationError
from fastkit_core.i18n import _
from typing import List, Dict

class BaseSchema(BaseModel):
    # Pydantic error type → translation key mapping
    VALIDATION_MESSAGE_MAP = {
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

        # Get translation key
        translation_key = cls.VALIDATION_MESSAGE_MAP.get(error_type, 'validation.value_error')

        # Prepare translation parameters
        params = {
            'field': field_name,
            **context  # Includes min_length, ge, le, etc.
        }

        # Translate
        translated = _(translation_key, **params)

        # If translation key not found, _(} returns the key itself
        # In that case, use default Pydantic message
        if translated == translation_key:
            return default_msg

        return translated