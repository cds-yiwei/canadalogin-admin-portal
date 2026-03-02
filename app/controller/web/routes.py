from ipaddress import ip_address
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger
from pydantic import TypeAdapter, ValidationError

from app.controller.schemas import (
    ApplicationAuditTrailResponse,
    ApplicationCreation,
    ApplicationDetailData,
    ApplicationListData,
    ApplicationTotalLoginsResponse,
)
from app.service.admin_service import AdminService
from app.service.authorization_service import AuthorizationService
from app.service.user_service import UserService
from app.auth.oidc import get_verify_oidc_client
from app.auth.role_mapper import map_claims_to_roles
from app.config import get_settings
from app.dependencies.auth import require_web_user
from app.dependencies.policies import get_authorization_service
from app.dependencies.services import get_admin_service, get_user_service
from app.utils.i18n import (
    get_request_locale,
    match_supported_locale,
    register_i18n,
    sanitize_next_url,
    translate,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
register_i18n(templates)
router = APIRouter()
settings = get_settings()
application_list_adapter = TypeAdapter(list[ApplicationListData])


def _extract_application_id(raw_app: dict) -> str | None:
    href = (((raw_app or {}).get("_links") or {}).get("self") or {}).get("href")
    if href:
        candidate = href.rstrip("/").split("/")[-1]
        if candidate and candidate.isdigit():
            return candidate

    for key in ("applicationId", "applicationUuid", "uuid", "id"):
        value = (raw_app or {}).get(key)
        if value:
            value_str = str(value).strip()
            if value_str:
                return value_str
    return None


def _parse_application_list(raw_items: Any) -> list[ApplicationListData]:
    if not isinstance(raw_items, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue

        href = str(((raw.get("_links") or {}).get("self") or {}).get("href") or "").strip()
        app_id = _extract_application_id(raw)
        app_name = str(raw.get("name") or "").strip()
        app_type = str(raw.get("type") or "").strip()

        if not app_id or not app_name or not app_type:
            continue

        normalized.append(
            {
                "app_id": app_id,
                "app_name": app_name,
                "app_type": app_type,
                "verify_href": href or None,
            }
        )

    if not normalized:
        return []

    try:
        return application_list_adapter.validate_python(normalized)
    except ValidationError as exc:  # noqa: BLE001
        logger.warning("Failed to validate application list payload: {}", exc)
        return []


def _normalize_epoch_seconds(raw_value: int | None) -> int | None:
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    if value > 10**11:
        return value // 1000
    return value


def _mask_email(value: str) -> str:
    value = str(value or "").strip()
    if not value or "@" not in value:
        return value

    local, domain = value.split("@", 1)
    local = local.strip()
    domain = domain.strip()
    if not local or not domain:
        return value

    prefix = local[:2]
    return f"{prefix}***@{domain}"


def _mask_ip(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return value

    try:
        parsed_ip = ip_address(value)
    except ValueError:
        return value

    if parsed_ip.version == 4:
        octets = value.split(".")
        if len(octets) == 4:
            return f"{octets[0]}.{octets[1]}.xxx.xxx"
        return value

    hextets = parsed_ip.exploded.split(":")
    if len(hextets) == 8:
        masked_tail = ["xxxx"] * 6
        return ":".join(hextets[:2] + masked_tail)
    return value


def _normalize_redirect_uris(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [line.strip() for line in str(raw_value).splitlines() if line.strip()]


def _normalize_checkbox(raw_value: str | None) -> str:
    if raw_value is None:
        return "false"
    return "true" if str(raw_value).strip().lower() in {"true", "1", "yes", "on"} else "false"


def _build_application_creation_payload(form_data: dict, owners: list[str]) -> dict:
    name = str(form_data.get("name") or "").strip()
    description = str(form_data.get("description") or "").strip()
    company_name = str(form_data.get("company_name") or "").strip()
    application_url = str(form_data.get("application_url") or "").strip()
    redirect_uris = _normalize_redirect_uris(form_data.get("redirect_uris"))
    pkce_enabled = _normalize_checkbox(form_data.get("pkce_enabled"))

    payload: dict[str, Any] = {
        "visibleOnLaunchpad": True,
        "customization": {"themeId": "default"},
        "name": name,
        "applicationState": True,
        "description": description,
        "templateId": "998",
        "owners": owners,
        "provisioning": {
            "policies": {
                "provPolicy": "disabled",
                "deProvPolicy": "disabled",
                "deProvAction": "delete",
                "adoptionPolicy": {
                    "matchingAttributes": [],
                    "remediationPolicy": {"policy": "NONE"},
                },
                "gracePeriod": 30,
            },
            "attributeMappings": [],
            "reverseAttributeMappings": [],
        },
        "attributeMappings": [],
        "providers": {
            "sso": {"userOptions": "oidc"},
            "oidc": {
                "properties": {
                    "doNotGenerateClientSecret": "false",
                    "additionalConfig": {
                        "oidcv3": True,
                        "requestObjectParametersOnly": "false",
                        "requestObjectSigningAlg": "RS256",
                        "requestObjectRequireExp": "true",
                        "certificateBoundAccessTokens": "false",
                        "dpopBoundAccessTokens": "false",
                        "validateDPoPProofJti": "false",
                        "dpopProofSigningAlg": "RS256",
                        "authorizeRspSigningAlg": "RS256",
                        "authorizeRspEncryptionAlg": "none",
                        "authorizeRspEncryptionEnc": "none",
                        "responseTypes": ["none", "code"],
                        "responseModes": [
                            "query",
                            "fragment",
                            "form_post",
                            "query.jwt",
                            "fragment.jwt",
                            "form_post.jwt",
                        ],
                        "clientAuthMethod": "default",
                        "requirePushAuthorize": "false",
                        "requestObjectMaxExpFromNbf": 1800,
                        "exchangeForSSOSessionOption": "default",
                        "subjectTokenTypes": ["urn:ietf:params:oauth:token-type:access_token"],
                        "actorTokenTypes": ["urn:ietf:params:oauth:token-type:access_token"],
                        "requestedTokenTypes": ["urn:ietf:params:oauth:token-type:access_token"],
                        "actorTokenRequired": False,
                        "logoutOption": "none",
                        "sessionRequired": False,
                        "requestUris": [],
                        "allowedClientAssertionVerificationKeys": [],
                    },
                    "generateRefreshToken": "false",
                    "renewRefreshToken": "true",
                    "idTokenEncryptAlg": "none",
                    "idTokenEncryptEnc": "none",
                    "grantTypes": {
                        "authorizationCode": "true",
                        "implicit": "false",
                        "clientCredentials": "false",
                        "ropc": "false",
                        "tokenExchange": "false",
                        "deviceFlow": "false",
                        "jwtBearer": "false",
                        "policyAuth": "false",
                    },
                    "accessTokenExpiry": 3600,
                    "refreshTokenExpiry": 86400,
                    "idTokenSigningAlg": "RS256",
                    "redirectUris": redirect_uris,
                },
                "token": {"accessTokenType": "default", "audiences": []},
                "grantProperties": {"generateDeviceFlowQRCode": "false"},
                "requirePkceVerification": pkce_enabled,
                "consentAction": "always_prompt",
                "applicationUrl": application_url,
                "scopes": [],
                "restrictEntitlements": True,
                "entitlements": [],
            },
            "saml": {"properties": {"companyName": company_name or None, "uniqueID": ""}},
        },
        "apiAccessClients": [],
    }
    return ApplicationCreation.model_validate(payload).model_dump(exclude_none=True)


def _parse_audit_trail(raw_payload: Any) -> list[dict[str, Any]]:
    parsed_payload: ApplicationAuditTrailResponse | None = None
    try:
        parsed_payload = ApplicationAuditTrailResponse.model_validate(raw_payload)
    except ValidationError as exc:  # noqa: BLE001
        logger.warning("Failed to validate audit trail payload: {}", exc)
        return []

    hits = parsed_payload.response.report.hits
    if not hits:
        return []

    rows: list[dict[str, Any]] = []
    for hit in hits:
        data = hit.source.data
        geoip = hit.source.geoip
        username_raw = str(data.username or "").strip()
        username_known = bool(username_raw) and username_raw.upper() != "UNKNOWN"
        origin_raw = str(data.origin or "").strip()
        ip_version: int | None = None
        if origin_raw:
            try:
                ip_version = ip_address(origin_raw).version
            except ValueError:
                ip_version = None

        result_raw = str(data.result or "").strip().lower()
        time_seconds = _normalize_epoch_seconds(hit.source.time)
        country = str(geoip.country_name or geoip.country_iso_code or "").strip()
        username_display = _mask_email(username_raw) if username_known else ""
        origin_display = _mask_ip(origin_raw)

        rows.append(
            {
                "username": username_raw,
                "username_display": username_display,
                "username_known": username_known,
                "origin": origin_raw,
                "origin_display": origin_display,
                "ip_version": ip_version,
                "result": result_raw,
                "time_seconds": time_seconds,
                "country": country,
            }
        )

    return rows


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    user: dict = Depends(require_web_user),
    service: UserService = Depends(get_user_service),
):
    applications = await service.get_applications()
    total_applications = applications.get("totalCount") if isinstance(applications, dict) else None
    if total_applications is None:
        embedded_apps = (
            (applications or {}).get("_embedded", {}) if isinstance(applications, dict) else {}
        )
        total_applications = len(embedded_apps.get("applications", []) or [])

    session = getattr(request, "session", {}) or {}
    flash_toast = session.pop("flash_toast", None)
    locale = get_request_locale(request)
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": user,
            "applications_total": total_applications,
            "title": translate(locale, "home.title"),
            "description": translate(locale, "home.description"),
            "breadcrumbs": [
                {"href": "/", "label": translate(locale, "breadcrumbs.dashboard")},
            ],
            "toast_flash": flash_toast,
        },
    )


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
async def oidc_callback(
    request: Request,
    authz_service: AuthorizationService = Depends(get_authorization_service),
):
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
    locale = match_supported_locale(lang)
    if locale:
        request.session["locale"] = locale
    next_url = sanitize_next_url(next) or "/"
    return RedirectResponse(url=next_url)


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: dict = Depends(require_web_user),
    service: UserService = Depends(get_user_service),
):
    profile = await service.get_profile()
    userinfo = await service.get_userinfo()
    applications = await service.get_applications()
    locale = get_request_locale(request)
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "profile": profile,
            "userinfo": userinfo,
            "applications": applications,
            "title": translate(locale, "profile.title"),
            "description": translate(locale, "profile.description"),
            "breadcrumbs": [
                {"href": "/", "label": translate(locale, "breadcrumbs.dashboard")},
                {"href": "/profile", "label": translate(locale, "breadcrumbs.profile")},
            ],
        },
    )


@router.get("/applications", response_class=HTMLResponse)
async def applications_page(
    request: Request,
    user: dict = Depends(require_web_user),
    service: UserService = Depends(get_user_service),
):
    applications = await service.get_applications()
    embedded = applications.get("_embedded", {}) if isinstance(applications, dict) else {}
    raw_items = embedded.get("applications", []) or []
    application_items = _parse_application_list(raw_items)
    total_applications = (
        applications.get("totalCount")
        if isinstance(applications, dict) and applications.get("totalCount") is not None
        else len(application_items)
    )
    session = getattr(request, "session", {}) or {}
    flash_toast = session.pop("flash_toast", None)
    locale = get_request_locale(request)
    return templates.TemplateResponse(
        "applications/list.html",
        {
            "request": request,
            "user": user,
            "applications": application_items,
            "applications_total": total_applications,
            "title": translate(locale, "applications.title"),
            "description": translate(locale, "applications.description"),
            "breadcrumbs": [
                {"href": "/", "label": translate(locale, "breadcrumbs.dashboard")},
                {"href": "/applications", "label": translate(locale, "breadcrumbs.applications")},
            ],
            "toast_flash": flash_toast,
        },
    )


@router.get("/applications/new", response_class=HTMLResponse)
async def application_create_page(
    request: Request,
    user: dict = Depends(require_web_user),
):
    locale = get_request_locale(request)
    return templates.TemplateResponse(
        "applications/new.html",
        {
            "request": request,
            "user": user,
            "grant_types": ["authorization_code"],
            "title": translate(locale, "applications.create.title"),
            "description": translate(locale, "applications.create.description"),
            "breadcrumbs": [
                {"href": "/", "label": translate(locale, "breadcrumbs.dashboard")},
                {"href": "/applications", "label": translate(locale, "breadcrumbs.applications")},
                {
                    "href": "/applications/new",
                    "label": translate(locale, "applications.create.title"),
                },
            ],
        },
    )


@router.post("/applications/new")
async def application_create_submit(
    request: Request,
    user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    locale = get_request_locale(request)
    form_data = await request.form()
    owner_id = (user or {}).get("id")
    owners: list[str] = [owner_id] if owner_id else []
    for value in form_data.getlist("owners"):
        owner_value = str(value).strip()
        if owner_value and owner_value not in owners:
            owners.append(owner_value)

    payload = _build_application_creation_payload(dict(form_data), owners)

    try:
        created = await service.create_application(payload)
        created_id = _extract_application_id(created)
        request.session["flash_toast"] = {
            "title": translate(locale, "applications.create.toast_success_title"),
            "body": translate(locale, "applications.create.toast_success_body"),
            "variant": "success",
        }
        if created_id:
            return RedirectResponse(
                url=f"/applications/{created_id}",
                status_code=status.HTTP_302_FOUND,
            )
        return RedirectResponse(url="/applications", status_code=status.HTTP_302_FOUND)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Application create failed: {}", exc)
        request.session["flash_toast"] = {
            "title": translate(locale, "applications.create.toast_error_title"),
            "body": translate(locale, "applications.create.toast_error_body"),
            "variant": "warning",
        }
        return RedirectResponse(url="/applications/new", status_code=status.HTTP_302_FOUND)


@router.get("/applications/{application_id}", response_class=HTMLResponse)
async def application_detail_page(
    request: Request,
    application_id: str,
    user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    application = await service.get_application_detail(application_id)
    if not isinstance(application, dict):
        application = {}

    parsed_application: ApplicationDetailData | None = None
    try:
        parsed_application = ApplicationDetailData.model_validate(application)
    except ValidationError as exc:  # noqa: BLE001
        logger.warning("Failed to validate application detail payload: {}", exc)

    session = getattr(request, "session", {}) or {}
    flash_toast = session.pop("flash_toast", None)
    locale = get_request_locale(request)
    breadcrumb_label = (
        parsed_application.name.strip() if parsed_application and parsed_application.name else ""
    ) or application_id
    application_payload = (
        parsed_application.model_dump(by_alias=True)
        if parsed_application is not None
        else application
    )
    return templates.TemplateResponse(
        "applications/detail.html",
        {
            "request": request,
            "user": user,
            "application_payload": application_payload,
            "app_id": application_id,
            "title": translate(locale, "applications.detail.title"),
            "description": translate(locale, "applications.detail.description"),
            "breadcrumbs": [
                {"href": "/", "label": translate(locale, "breadcrumbs.dashboard")},
                {"href": "/applications", "label": translate(locale, "breadcrumbs.applications")},
                {"href": f"/applications/{application_id}", "label": breadcrumb_label},
            ],
            "toast_flash": flash_toast,
        },
    )


@router.delete("/applications/{application_id}")
async def delete_application(
    request: Request,
    application_id: str,
    _user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    locale = get_request_locale(request)
    try:
        await service.delete_application(application_id)
        request.session["flash_toast"] = {
            "title": translate(locale, "applications.detail.delete_success_title"),
            "body": translate(locale, "applications.detail.delete_success_body"),
            "variant": "success",
        }
        return Response(
            status_code=status.HTTP_204_NO_CONTENT, headers={"HX-Redirect": "/applications"}
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Application delete failed: {}", exc)
        request.session["flash_toast"] = {
            "title": translate(locale, "applications.detail.delete_error_title"),
            "body": translate(locale, "applications.detail.delete_error_body"),
            "variant": "warning",
        }
        return Response(
            status_code=status.HTTP_200_OK,
            headers={"HX-Redirect": f"/applications/{application_id}"},
        )


@router.get("/applications/{application_id}/usage", response_class=HTMLResponse)
async def application_usage_page(
    request: Request,
    application_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    size: int = 50,
    sort_by: str = "time",
    sort_order: str = "DESC",
    user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    application = await service.get_application_detail(application_id)
    if not isinstance(application, dict):
        application = {}

    parsed_application: ApplicationDetailData | None = None
    try:
        parsed_application = ApplicationDetailData.model_validate(application)
    except ValidationError as exc:  # noqa: BLE001
        logger.warning("Failed to validate application detail payload: {}", exc)

    app_name = (
        parsed_application.name.strip()
        if parsed_application and parsed_application.name and parsed_application.name.strip()
        else ""
    )

    total_logins = await service.get_application_total_logins(application_id, from_date, to_date)
    parsed_total_logins: ApplicationTotalLoginsResponse | None = None
    try:
        parsed_total_logins = ApplicationTotalLoginsResponse.model_validate(total_logins)
    except ValidationError as exc:  # noqa: BLE001
        logger.warning("Failed to validate total logins payload: {}", exc)

    total_logins_summary = {
        "successful": 0,
        "failed": 0,
        "unique_users": 0,
    }
    if parsed_total_logins:
        report = parsed_total_logins.response.report
        total_logins_summary = {
            "successful": report.successful_logins.doc_count,
            "failed": report.failed_logins.doc_count,
            "unique_users": report.unique_users.value,
        }
    audit_trail = await service.get_application_audit_trail(
        application_id,
        from_date,
        to_date,
        size,
        sort_by,
        sort_order,
    )
    audit_trail_rows = _parse_audit_trail(audit_trail)

    locale = get_request_locale(request)
    breadcrumb_label = app_name or application_id
    return templates.TemplateResponse(
        "applications/usage.html",
        {
            "request": request,
            "user": user,
            "app_id": application_id,
            "app_name": app_name or application_id,
            "total_logins": total_logins,
            "total_logins_summary": total_logins_summary,
            "audit_trail": audit_trail,
            "audit_trail_rows": audit_trail_rows,
            "title": translate(locale, "applications.usage.title"),
            "description": translate(locale, "applications.usage.description"),
            "breadcrumbs": [
                {"href": "/", "label": translate(locale, "breadcrumbs.dashboard")},
                {"href": "/applications", "label": translate(locale, "breadcrumbs.applications")},
                {"href": f"/applications/{application_id}", "label": breadcrumb_label},
                {
                    "href": f"/applications/{application_id}/usage",
                    "label": translate(locale, "applications.actions.usage"),
                },
            ],
        },
    )
