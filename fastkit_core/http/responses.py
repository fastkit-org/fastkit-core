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
            items=[item.to_dict() for item in items],
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

def _serialize(obj: Any) -> Any:
    """Serialize a single item to a JSON-safe value."""
    if hasattr(obj, 'model_dump'):  # Pydantic v2
        return obj.model_dump()
    if hasattr(obj, 'dict'):        # Pydantic v1
        return obj.dict()
    return obj
