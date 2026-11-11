"""HTTP Basic Auth middleware for the FastAPI API (viva / lab deployments).

When ``API_BASIC_AUTH_PASSWORD`` is empty, auth is disabled for local development.
"""

from __future__ import annotations

import base64
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Require HTTP Basic credentials on /api/* when a password is configured."""

    _PUBLIC_EXACT = frozenset({"/", "/openapi.json"})
    _PUBLIC_PREFIXES = ("/docs", "/redoc")

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._username = os.getenv("API_BASIC_AUTH_USERNAME", "analyst")
        self._password = os.getenv("API_BASIC_AUTH_PASSWORD", "").strip()

    def _is_public(self, path: str) -> bool:
        if path in self._PUBLIC_EXACT:
            return True
        if any(path.startswith(prefix) for prefix in self._PUBLIC_PREFIXES):
            return True
        if path == "/api/health" or path.startswith("/api/media"):
            return True
        return False

    async def dispatch(self, request: Request, call_next):
        if not self._password or self._is_public(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return JSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="SOCMINT API"'},
                content={"detail": "Missing or invalid Authorization header"},
            )

        try:
            decoded = base64.b64decode(auth_header[6:].strip()).decode("utf-8")
            user, pwd = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return JSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="SOCMINT API"'},
                content={"detail": "Invalid Basic Auth credentials"},
            )

        user_ok = secrets.compare_digest(user, self._username)
        pwd_ok = secrets.compare_digest(pwd, self._password)
        if not (user_ok and pwd_ok):
            return JSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="SOCMINT API"'},
                content={"detail": "Unauthorized"},
            )

        return await call_next(request)
