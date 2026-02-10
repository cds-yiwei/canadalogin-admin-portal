import time
from typing import Any, Dict

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.oidc import refresh_token
from app.config import get_settings
from app.repository.iv_user_client import get_user_http_client


class TokenRefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith(("/auth", "/health", "/static")):
            return await call_next(request)

        session = request.scope.get("session") or {}
        tokens = session.get("tokens") or {}
        access_token = tokens.get("access_token")
        refresh_token_value = tokens.get("refresh_token")
        expires_at = tokens.get("expires_at")

        if not access_token or not refresh_token_value or not expires_at:
            return await call_next(request)

        settings = get_settings()
        now = int(time.time())
        try:
            expires_at_int = int(expires_at)
        except (TypeError, ValueError):
            return await call_next(request)

        if expires_at_int - now > settings.token_refresh_leeway_seconds:
            return await call_next(request)

        http_client = get_user_http_client(request)
        try:
            refreshed = await refresh_token(http_client, refresh_token_value)
        except Exception as exc:  # noqa: BLE001
            session.clear()
            logger.exception("Token refresh failed: {}", exc)
            return await call_next(request)

        refreshed_tokens = _merge_tokens(tokens, refreshed, now)
        session["tokens"] = refreshed_tokens
        return await call_next(request)


def _merge_tokens(existing: Dict[str, Any], refreshed: Dict[str, Any], now: int) -> Dict[str, Any]:
    updated = dict(existing)
    if refreshed.get("access_token"):
        updated["access_token"] = refreshed.get("access_token")
    if refreshed.get("refresh_token"):
        updated["refresh_token"] = refreshed.get("refresh_token")
    if refreshed.get("id_token"):
        updated["id_token"] = refreshed.get("id_token")
    if refreshed.get("token_type"):
        updated["token_type"] = refreshed.get("token_type")

    if refreshed.get("expires_at"):
        updated["expires_at"] = refreshed.get("expires_at")
    else:
        expires_in = refreshed.get("expires_in")
        if expires_in:
            try:
                updated["expires_at"] = now + int(expires_in)
            except (TypeError, ValueError):
                pass

    return updated
