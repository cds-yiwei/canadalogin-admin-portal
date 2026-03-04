import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse


class WebSessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # When SKIP_SESSION_STORE is set (tests/local static checks), session middleware is not added.
        # Bypass middleware checks so dependency-based auth can control behavior.
        if os.environ.get("SKIP_SESSION_STORE"):
            return await call_next(request)

        if request.url.path.startswith(("/auth", "/api", "/health", "/locale", "/static")):
            return await call_next(request)
        session = request.scope.get("session") or {}
        if not session.get("user"):
            return RedirectResponse(url="/auth/login")
        return await call_next(request)


class ApiSessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Skip session enforcement in lightweight test/dev runs when session store is disabled.
        if os.environ.get("SKIP_SESSION_STORE"):
            return await call_next(request)

        if not request.url.path.startswith("/api"):
            return await call_next(request)
        if request.url.path.startswith("/api/health"):
            return await call_next(request)
        session = request.scope.get("session") or {}
        if not session.get("user"):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        return await call_next(request)
