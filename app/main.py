from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starsessions import SessionAutoloadMiddleware, SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from loguru import logger

from app.controller.api.routes import router as api_router
from app.config import get_settings
from app.repository.iv_admin_client import close_admin_api_client, init_admin_api_client
from app.repository.iv_user_client import close_user_http_client, init_user_http_client
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.auth_mw import ApiSessionAuthMiddleware, WebSessionAuthMiddleware
from app.middleware.error_handlers import add_error_handlers
from app.middleware.locale_mw import LocaleMiddleware
from app.middleware.token_refresh_mw import TokenRefreshMiddleware
from app.repository.session_store import (
    close_session_store,
    get_session_store,
    init_session_store,
    setup_session_store,
)
from app.controller.web.routes import router as web_router
from app.controller.web.fragments import router as fragments_router

BASE_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            await init_admin_api_client(app, settings)
            await init_user_http_client(app)
            await init_session_store(app, settings)

            yield
        finally:
            await close_session_store(app)
            await close_user_http_client(app)
            await close_admin_api_client(app)

    app = FastAPI(title="CanadaLogin Admin Site", lifespan=lifespan)

    logger.info("Initializing CanadaLogin Admin Site FastAPI application")

    app.add_middleware(ProxyHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(ApiSessionAuthMiddleware)
    app.add_middleware(WebSessionAuthMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(LocaleMiddleware)
    app.add_middleware(TokenRefreshMiddleware)

    # Autoload session if cookie is present
    app.add_middleware(SessionAutoloadMiddleware)
    # Order matters: add session middleware last so it runs first and sets request.session
    setup_session_store(app, settings)
    session_store = get_session_store(app)
    app.add_middleware(
        SessionMiddleware,
        store=session_store,
        rolling=True,
        cookie_domain=settings.session_cookie_domain,
        cookie_name=settings.session_cookie_name,
        cookie_https_only=settings.session_cookie_secure,
        lifetime=settings.session_lifetime,
    )

    # Serve static assets used by Jinja templates
    static_dir = BASE_DIR / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    add_error_handlers(app)

    app.include_router(api_router)
    app.include_router(web_router)
    app.include_router(fragments_router)

    return app
