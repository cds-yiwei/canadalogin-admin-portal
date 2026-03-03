from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger

from app.auth.oidc import get_verify_oidc_client
from app.auth.role_mapper import map_claims_to_roles
from app.dependencies.policies import get_authorization_service
from app.utils.i18n import get_request_locale, translate
from app.controller.web._utils import templates, settings

router = APIRouter()


@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    locale = get_request_locale(request)
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "title": translate(locale, "login.title"),
            "description": translate(locale, "login.description"),
            "breadcrumbs": [
                {"href": "/auth/login", "label": translate(locale, "breadcrumbs.sign_in")},
            ],
        },
    )


@router.get("/auth/oidc/start")
async def oidc_login(request: Request):
    redirect_uri = settings.oidc_redirect_uri
    verify_oidc_client = get_verify_oidc_client()
    return await verify_oidc_client.authorize_redirect(request, redirect_uri=redirect_uri)


@router.get("/auth/oidc/callback")
async def oidc_callback(request: Request, authz_service=Depends(get_authorization_service)):
    """Handle OIDC callback."""
    try:
        locale = get_request_locale(request)
        verify_oidc_client = get_verify_oidc_client()
        oidc_response = await verify_oidc_client.authorize_access_token(request)

        userinfo = oidc_response.get("userinfo") or {}
        if not userinfo:
            raise ValueError("userinfo missing from OIDC response")

        raw_roles = userinfo.get("groupIds") or []
        if isinstance(raw_roles, str):
            raw_roles = [raw_roles]
        allowed_groups = {"admin", "application owners", "developer"}
        raw_roles = [r for r in raw_roles if str(r).lower() in allowed_groups]
        roles = map_claims_to_roles(raw_roles)
        permissions = authz_service.resolve_permissions(roles)

        user = {
            "id": userinfo.get("sub") or userinfo.get("id") or userinfo.get("email") or "unknown",
            "email": userinfo.get("email", ""),
            "display_name": userinfo.get("name")
            or userinfo.get("preferred_username")
            or userinfo.get("email", ""),
            "roles": [role.value for role in roles],
            "permissions": permissions,
        }

        request.session["user"] = user
        request.session["tokens"] = {
            "access_token": oidc_response.get("access_token"),
            "refresh_token": oidc_response.get("refresh_token"),
            "id_token": oidc_response.get("id_token"),
            "token_type": oidc_response.get("token_type"),
            "expires_at": oidc_response.get("expires_at"),
        }

        request.session["flash_toast"] = {
            "title": translate(locale, "toast.signed_in_title"),
            "body": translate(locale, "toast.welcome_back", name=user["display_name"]),
            "variant": "success",
        }

        return RedirectResponse(url="/")
    except Exception as exc:  # noqa: BLE001
        logger.exception("OIDC callback failed: {}", exc)
        return RedirectResponse(url="/auth/login")


@router.get("/auth/logout")
async def logout(request: Request):
    session = getattr(request, "session", None)
    if session is not None:
        session.clear()
    return RedirectResponse(url="/auth/login")


@router.get("/locale")
async def set_locale(request: Request, lang: str, next: str | None = None):
    # reuse match_supported_locale and sanitize_next_url from utils if needed
    from app.utils.i18n import match_supported_locale, sanitize_next_url

    new_locale = match_supported_locale(lang)
    if new_locale:
        request.session["locale"] = new_locale
    next_url = sanitize_next_url(next) or "/"
    return RedirectResponse(url=next_url)
