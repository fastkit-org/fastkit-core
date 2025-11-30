from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request.

    Adds request ID to:
    - request.state.request_id (accessible in route handlers)
    - X-Request-ID response header (for client/logging)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        return response


class LocaleMiddleware(BaseHTTPMiddleware):
    """
    Set locale from request headers, query params, or cookies.

    Priority:
    1. Accept-Language header
    2. ?lang= query parameter
    3. locale cookie
    4. Default: 'en'
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get locale from header, query param, or cookie
        locale = (
                request.headers.get('Accept-Language', '')[:2]
                or request.query_params.get('lang')
                or request.cookies.get('locale')
                or 'en'
        )

        from fastkit_core.i18n import set_locale
        set_locale(locale)

        response = await call_next(request)
        return response