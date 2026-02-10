from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse


class WebSessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith(("/auth", "/api", "/health", "/locale", "/static")):
            return await call_next(request)
        session = request.scope.get("session") or {}
        if not session.get("user"):
            return RedirectResponse(url="/auth/login")
        return await call_next(request)


class ApiSessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        if request.url.path.startswith("/api/health"):
            return await call_next(request)
        session = request.scope.get("session") or {}
        if not session.get("user"):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        return await call_next(request)
