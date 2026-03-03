from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from loguru import logger

from app.service.user_service import UserService
from app.service.admin_service import AdminService
from app.dependencies.auth import require_web_user
from app.dependencies.services import get_user_service, get_admin_service
from app.controller.web._utils import (
    templates,
    get_request_locale,
    translate,
    _parse_application_list,
    _extract_application_id,
    _build_application_creation_payload,
    _normalize_epoch_seconds,
)
from app.controller.schemas import (
    ApplicationDetailData,
    ApplicationTotalLoginsResponse,
    ApplicationAuditTrailResponse,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, user: dict = Depends(require_web_user), service: UserService = Depends(get_user_service)):
    applications = await service.get_applications()
    total_applications = applications.get("totalCount") if isinstance(applications, dict) else None
    if total_applications is None:
        embedded_apps = ((applications or {}).get("_embedded", {}) if isinstance(applications, dict) else {})
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
            "breadcrumbs": [{"href": "/", "label": translate(locale, "breadcrumbs.dashboard")}],
            "toast_flash": flash_toast,
        },
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: dict = Depends(require_web_user), service: UserService = Depends(get_user_service)):
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
async def applications_page(request: Request, user: dict = Depends(require_web_user), service: UserService = Depends(get_user_service)):
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
async def application_create_page(request: Request, user: dict = Depends(require_web_user)):
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
                {"href": "/applications/new", "label": translate(locale, "applications.create.title")},
            ],
        },
    )


@router.post("/applications/new")
async def application_create_submit(request: Request, user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
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
            return RedirectResponse(url=f"/applications/{created_id}", status_code=status.HTTP_302_FOUND)
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
async def application_detail_page(request: Request, application_id: str, user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
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
        parsed_application.model_dump(by_alias=True) if parsed_application is not None else application
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
async def delete_application(request: Request, application_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
    locale = get_request_locale(request)
    try:
        await service.delete_application(application_id)
        request.session["flash_toast"] = {
            "title": translate(locale, "applications.detail.delete_success_title"),
            "body": translate(locale, "applications.detail.delete_success_body"),
            "variant": "success",
        }
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"HX-Redirect": "/applications"})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Application delete failed: {}", exc)
        request.session["flash_toast"] = {
            "title": translate(locale, "applications.detail.delete_error_title"),
            "body": translate(locale, "applications.detail.delete_error_body"),
            "variant": "warning",
        }
        return Response(status_code=status.HTTP_200_OK, headers={"HX-Redirect": f"/applications/{application_id}"})


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
        parsed_application.name.strip() if parsed_application and parsed_application.name and parsed_application.name.strip() else ""
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
        application_id, from_date, to_date, size, sort_by, sort_order
    )

    # parse audit trail rows using helper in utils
    from app.controller.web._utils import _parse_audit_trail as parse_audit_trail

    audit_trail_rows = parse_audit_trail(audit_trail)

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
                {"href": f"/applications/{application_id}/usage", "label": translate(locale, "applications.actions.usage")},
            ],
        },
    )
