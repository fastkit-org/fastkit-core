from typing import Any
from starlette.responses import JSONResponse


def success_response(
        data: Any = None,
        message: str | None = None,
        status_code: int = 200
) -> JSONResponse:
    """Standard success response format."""
    return JSONResponse(
        content={
            'data': data,
            'message': message
        },
        status_code=status_code
    )


def error_response(
        message: str,
        errors: dict | None = None,
        status_code: int = 400
) -> JSONResponse:
    """Standard error response format."""
    return JSONResponse(
        content={
            'errors': errors,
            'message': message
        },
        status_code=status_code
    )

def paginated_response(
        items: list,
        total: int,
        page: int,
        per_page: int,
        message: str | None = None
) -> JSONResponse:
    """Paginated response with metadata."""
    return JSONResponse(
        content={
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'message': message
        },
        status_code=200
    )
