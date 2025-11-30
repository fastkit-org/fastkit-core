from starlette.middleware.base import BaseHTTPMiddleware
import uuid


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request."""

    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        return response


class LocaleMiddleware(BaseHTTPMiddleware):
    """Set locale from request headers."""

    async def dispatch(self, request, call_next):
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