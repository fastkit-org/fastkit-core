from typing import Any
from pydantic import ValidationError
from pydantic_core import InitErrorDetails

def raise_validation_error(field: str, message: str, value: Any = None) -> None:
    raise ValidationError.from_exception_data(
        'ValidationError',
        [
            InitErrorDetails(
                type='value_error',
                loc=(field,),
                input=value,
                ctx={'error': ValueError(message)}
            )
        ]
    )

def raise_multiple_validation_errors(errors: list[tuple[str, str, Any]]) -> None:
    """errors: list of (field, message, value) tuples"""
    raise ValidationError.from_exception_data(
        'ValidationError',
        [
            InitErrorDetails(
                type='value_error',
                loc=(field,),
                input=value,
                ctx={'error': ValueError(message)}
            )
            for field, message, value in errors
        ]
    )

def format_validation_errors(errors: list[dict]) -> dict[str, list[str]]:
    """Parse raw Pydantic/FastAPI error list into {field: [messages]} format."""
    formatted = {}
    for error in errors:
        field = str(error['loc'][-1]) if error.get('loc') else 'unknown'
        if field not in formatted:
            formatted[field] = []
        formatted[field].append(error['msg'])
    return formatted