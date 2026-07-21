"""Standardized error envelope for the /api/v1 surface only
(docs/v3/10_API_SPECIFICATION.md's Standard Response Format).

V2's existing routers raise plain fastapi.HTTPException and rely on
FastAPI's default {"detail": ...} shape - that behavior is left
completely untouched. New /api/v1 code raises APIError instead, which
only this module's handler recognizes, so the two response shapes never
collide. The RequestValidationError handler is the one place that must
actively branch by path, since FastAPI installs it globally.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Raised by /api/v1 routes/dependencies for a client-facing error.

    Never raised by V2 code - see module docstring.
    """

    def __init__(self, status_code: int, message: str, errors: list | None = None):
        self.status_code = status_code
        self.message = message
        self.errors = errors or []


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.message, "errors": exc.errors},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        if request.url.path.startswith("/api/v1"):
            return JSONResponse(
                status_code=422,
                content={"success": False, "message": "Validation error.", "errors": exc.errors()},
            )
        # Reproduces FastAPI's own default RequestValidationError body
        # exactly, so every existing V2 route/test is unaffected.
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
