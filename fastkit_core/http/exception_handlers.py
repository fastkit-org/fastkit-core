"""
FastAPI exception handlers for FastKit.

Automatically formats exceptions into standard response format.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from fastkit_core.http.responses import error_response
from fastkit_core.http.exceptions import FastKitException
from fastkit_core.i18n import _
import logging

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all FastKit exception handlers.

    Call this once when creating your FastAPI app:

    Example:
        from fastapi import FastAPI
        from fastkit_core.http import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """

    @app.exception_handler(FastKitException)
    async def fastkit_exception_handler(
            request: Request,
            exc: FastKitException
    ):
        """Handle FastKit custom exceptions."""
        return error_response(
            message=exc.message,
            errors=exc.errors,
            status_code=exc.status_code
        )

    @app.exception_handler(RequestValidationError)
    async def fastapi_validation_handler(
            request: Request,
            exc: RequestValidationError
    ):
        """Handle FastAPI request validation errors."""
        from fastkit_core.validation import BaseSchema

        # Convert Pydantic errors to FastKit format
        errors = {}
        for error in exc.errors():
            field = str(error['loc'][-1]) if error['loc'] else 'unknown'
            if field not in errors:
                errors[field] = []
            errors[field].append(error['msg'])

        return error_response(
            message=_('validation.failed'),
            errors=errors,
            status_code=422
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
            request: Request,
            exc: ValidationError
    ):
        """Handle Pydantic validation errors."""
        from fastkit_core.validation import BaseSchema
        errors = BaseSchema.format_errors(exc)

        return error_response(
            message=_('validation.failed'),
            errors=errors,
            status_code=422
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
            request: Request,
            exc: Exception
    ):
        """Handle unexpected exceptions."""
        # Log the error
        logger.error(f"Unexpected error: {exc}", exc_info=True)

        # Check if DEBUG mode
        from fastkit_core.config import config
        debug = config('app.DEBUG', False)

        if debug:
            # Show detailed error in development
            return error_response(
                message=str(exc),
                status_code=500
            )
        else:
            # Hide details in production
            return error_response(
                message=_('errors.internal_server_error'),
                status_code=500
            )