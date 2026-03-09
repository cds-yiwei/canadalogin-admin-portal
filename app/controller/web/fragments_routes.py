from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from app.dependencies.auth import require_web_user
from app.dependencies.services import get_admin_service
from app.controller.web._utils import templates, get_request_locale, translate

router = APIRouter()


@router.get("/fragments/application-info/edit", response_class=HTMLResponse)
async def fragment_application_info_edit(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    return templates.TemplateResponse(request, "fragments/application_info_edit.html", {"request": request, "application_payload": application, "app_id": app_id, "title": translate(locale, "applications.detail.title")})


@router.get("/fragments/oidc-settings/edit", response_class=HTMLResponse)
async def fragment_oidc_settings_edit(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    return templates.TemplateResponse(request, "fragments/oidc_settings_edit.html", {"request": request, "application_payload": application, "app_id": app_id, "title": translate(locale, "applications.detail.title")})


@router.get("/fragments/single-logout/edit", response_class=HTMLResponse)
async def fragment_single_logout_edit(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    # Compute logout_option for template convenience
    application_payload = application or {}
    logout_option = None
    try:
        logout_option = (
            application_payload.get("providers", {}).get("oidc", {}).get("properties", {}).get("additionalConfig", {}).get("logoutOption")
        )
    except Exception:
        logout_option = None
    return templates.TemplateResponse(request, "fragments/single_logout_edit.html", {"request": request, "application_payload": application, "app_id": app_id, "logout_option": logout_option, "title": translate(locale, "applications.detail.title")})


@router.get("/fragments/people/edit", response_class=HTMLResponse)
async def fragment_people_edit(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    return templates.TemplateResponse(request, "fragments/people_edit.html", {"request": request, "application_payload": application, "app_id": app_id, "title": translate(locale, "applications.detail.title")})


# POST handlers
@router.post("/applications/{app_id}/edit/application-info")
async def submit_application_info(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    form = await request.form()
    payload = {
        "name": form.get("name"),
        "description": form.get("description"),
        "providers": {"saml": {"properties": {"companyName": form.get("companyName")}}, "oidc": {"applicationUrl": form.get("applicationUrl")}},
    }
    try:
        await service.update_application_section(app_id, "application_info", dict(payload))
        # Return updated fragment (redirect to detail view fragment)
        application = await service.get_application_detail(app_id)
        return templates.TemplateResponse(request, "fragments/application_info_edit.html", {"request": request, "application_payload": application, "app_id": app_id})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/oidc-settings")
async def submit_oidc_settings(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    form = await request.form()
    redirect_text = form.get("redirectUris") or ""
    redirect_uris = [line.strip() for line in redirect_text.splitlines() if line.strip()]
    require_pkce = True if form.get("requirePkceVerification") == "true" or form.get("requirePkceVerification") == "on" else False
    payload = {"providers": {"oidc": {"properties": {"redirectUris": redirect_uris}, "requirePkceVerification": require_pkce}}}
    try:
        await service.update_application_section(app_id, "oidc_settings", payload)
        application = await service.get_application_detail(app_id)
        return templates.TemplateResponse(request, "fragments/oidc_settings_edit.html", {"request": request, "application_payload": application, "app_id": app_id})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/single-logout")
async def submit_single_logout(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    form = await request.form()
    logout_option = form.get("logoutOption")
    logout_uri = form.get("logoutURI")
    redirect_text = form.get("logoutRedirectURIs") or ""
    redirect_uris = [line.strip() for line in redirect_text.splitlines() if line.strip()]
    payload = {"providers": {"oidc": {"properties": {"additionalConfig": {"logoutOption": logout_option, "logoutURI": logout_uri, "logoutRedirectURIs": redirect_uris}}}}}
    try:
        await service.update_application_section(app_id, "single_logout", payload)
        application = await service.get_application_detail(app_id)
        return templates.TemplateResponse(request, "fragments/single_logout_edit.html", {"request": request, "application_payload": application, "app_id": app_id})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/people")
async def submit_people(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    form = await request.form()
    owners_text = form.get("owners") or ""
    owners = [email.strip() for email in owners_text.splitlines() if email.strip()]
    payload = {"owners": [{"email": o} for o in owners]}
    try:
        await service.update_application_section(app_id, "people", payload)
        application = await service.get_application_detail(app_id)
        return templates.TemplateResponse(request, "fragments/people_edit.html", {"request": request, "application_payload": application, "app_id": app_id})
    except NotImplementedError:
        return Response(status_code=501)
