from typing import Any
from starlette.responses import JSONResponse


def success_response(
    data: Any = None,
    message: str | None = None,
    status_code: int = 200
) -> JSONResponse:
    """Standard success response format."""
    return JSONResponse({
        'data': data,
        'message': message
    }, status_code=status_code)

def error_response(
    message: str,
    errors: dict | None = None,
    status_code: int = 400
) -> JSONResponse:
    """Standard error response format."""
    return JSONResponse({
        'errors': errors,
        'message': message
    }, status_code=status_code)
