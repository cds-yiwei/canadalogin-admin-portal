from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils.i18n import DEFAULT_LOCALE, match_supported_locale, select_locale


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session = request.scope.get("session") or {}
        query_lang = request.query_params.get("lang")
        locale = None

        if query_lang:
            locale = match_supported_locale(query_lang) or DEFAULT_LOCALE
            if session is not None:
                session["locale"] = locale
        else:
            session_locale = session.get("locale") if session is not None else None
            if session_locale:
                locale = match_supported_locale(session_locale)
            if not locale:
                locale = select_locale(request.headers.get("accept-language"))
                if session is not None and "locale" not in session:
                    session["locale"] = locale

        request.state.locale = locale or DEFAULT_LOCALE
        response = await call_next(request)
        response.headers.setdefault("Content-Language", request.state.locale)
        return response
