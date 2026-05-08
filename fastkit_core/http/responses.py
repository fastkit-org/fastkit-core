from typing import Any
from starlette.responses import JSONResponse


def success_response(
        data: Any = None,
        message: str | None = None,
        status_code: int = 200
) -> JSONResponse:
    """
    Standard success response format.

    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code (default: 200)

    Returns:
        JSONResponse with format:
        {
            "success": true,
            "data": {...},
            "message": "..." (optional)
        }
    """
    content = {
        'success': True,
        'data': _serialize(data) if data is not None else data
    }

    if message:
        content['message'] = message

    return JSONResponse(content=content, status_code=status_code)


def error_response(
        message: str,
        errors: dict | None = None,
        status_code: int = 400,
        headers: dict | None = None
) -> JSONResponse:
    """
    Standard error response format.

    Args:
        message: Error message
        errors: Optional error details (e.g., validation errors)
        status_code: HTTP status code (default: 400)
        headers: Dictionary of headers

    Returns:
        JSONResponse with format:
        {
            "success": false,
            "message": "...",
            "errors": {...} (optional)
        }
    """
    content = {
        'success': False,
        'message': message
    }

    if errors:
        content['errors'] = errors

    return JSONResponse(content=content, status_code=status_code, headers=headers)


def paginated_response(
        items: list,
        pagination: dict,
        message: str | None = None,
        status_code: int = 200
) -> JSONResponse:
    """
    Paginated response with metadata.

    Args:
        items: List of items
        pagination: Pagination metadata from repository
                   Should include: page, per_page, total, total_pages, has_next, has_prev
        message: Optional message
        status_code: HTTP status code (default: 200)

    Returns:
        JSONResponse with format:
        {
            "success": true,
            "data": [...],
            "pagination": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": true,
                "has_prev": false
            },
            "message": "..." (optional)
        }

    Example:
        items, metadata = service.paginate(page=1, per_page=20)
        return paginated_response(
            items=items
            pagination=metadata
        )
    """
    content = {
        'success': True,
        'data': [_serialize(item) for item in items],
        'pagination': pagination
    }

    if message:
        content['message'] = message

    return JSONResponse(content=content, status_code=status_code)

def cursor_paginated_response(
        items: list,
        next_cursor: str | None,
        per_page: int,
        message: str | None = None,
        status_code: int = 200
) -> JSONResponse:
    """
    Cursor-based paginated response.

    Args:
        items:       List of items for the current page.
        next_cursor: Opaque cursor string for the next page, or None on the last page.
        per_page:    Page size used for this request.
        message:     Optional message.
        status_code: HTTP status code (default: 200).

    Returns:
        JSONResponse with format:
        {
            "success": true,
            "data": [...],
            "pagination": {
                "next_cursor": "eyJpZCI6IDIwfQ==",
                "per_page": 20,
                "has_next": true
            },
            "message": "..." (optional)
        }

    Example:
        items, next_cursor = await service.cursor_paginate(
            cursor=cursor,
            per_page=per_page,
            cursor_field='id',
        )
        return cursor_paginated_response(
            items=items,
            next_cursor=next_cursor,
            per_page=per_page,
        )
    """
    content = {
        'success': True,
        'data': [_serialize(item) for item in items],
        'pagination': {
            'next_cursor': next_cursor,
            'per_page': per_page,
            'has_next': next_cursor is not None,
        }
    }

    if message:
        content['message'] = message

    return JSONResponse(content=content, status_code=status_code)


def _serialize(obj: Any) -> Any:
    """Recursively serialize to a JSON-safe value."""
    if hasattr(obj, 'model_dump'):  # Pydantic v2
        return obj.model_dump()
    if hasattr(obj, 'dict'):  # Pydantic v1
        return obj.dict()
    if hasattr(obj, '__table__'):  # SQLAlchemy model
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj
