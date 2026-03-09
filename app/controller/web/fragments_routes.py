from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from app.dependencies.auth import require_web_user
from app.dependencies.services import get_admin_service
from app.controller.web._utils import templates, get_request_locale, translate
import re
import json

router = APIRouter(prefix="/fragments", tags=["fragments-edit"]) 


def _is_valid_url(value: str) -> bool:
    if not value:
        return False
    # simple URL check
    return bool(re.match(r"^https?://[\w\-\.]+(:\d+)?(/.*)?$", value))


def _is_valid_email(value: str) -> bool:
    if not value:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))


def _error_response(request: Request, template: str, context: dict, status_code: int = 400):
    # when returning errors to HTMX, render template with errors and return 400
    return templates.TemplateResponse(request, template, context, status_code=status_code)


@router.get("/application-info/edit", response_class=HTMLResponse)
async def fragment_application_info_edit(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    return templates.TemplateResponse(request, "fragments/application_info_edit.html", {"request": request, "application_payload": application, "app_id": app_id, "title": translate(locale, "applications.detail.title")})


@router.get("/oidc-settings/edit", response_class=HTMLResponse)
async def fragment_oidc_settings_edit(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    return templates.TemplateResponse(request, "fragments/oidc_settings_edit.html", {"request": request, "application_payload": application, "app_id": app_id, "title": translate(locale, "applications.detail.title")})


@router.get("/single-logout/edit", response_class=HTMLResponse)
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


@router.get("/people/edit", response_class=HTMLResponse)
async def fragment_people_edit(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    return templates.TemplateResponse(request, "fragments/people_edit.html", {"request": request, "application_payload": application, "app_id": app_id, "title": translate(locale, "applications.detail.title")})


# POST handlers
@router.post("/applications/{app_id}/edit/application-info")
async def submit_application_info(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    form = await request.form()
    name = str(form.get("name") or "").strip()
    description = str(form.get("description") or "").strip()
    company = str(form.get("companyName") or "").strip()
    application_url = str(form.get("applicationUrl") or "").strip()

    errors: dict = {}
    if not name:
        errors["name"] = translate(get_request_locale(request), "validation.required")
    elif len(name) > 200:
        errors["name"] = translate(get_request_locale(request), "validation.max_length", length=200)
    if description and len(description) > 1000:
        errors["description"] = translate(get_request_locale(request), "validation.max_length", length=1000)
    if company and len(company) > 200:
        errors["companyName"] = translate(get_request_locale(request), "validation.max_length", length=200)
    if application_url and not _is_valid_url(application_url):
        errors["applicationUrl"] = translate(get_request_locale(request), "validation.invalid_url")

    if errors:
        context = {"request": request, "application_payload": {"name": name, "description": description, "providers": {"saml": {"properties": {"companyName": company}}, "oidc": {"applicationUrl": application_url}}}, "app_id": app_id, "errors": errors}
        return _error_response(request, "fragments/application_info_edit.html", context)

    payload = {
        "name": name,
        "description": description,
        "providers": {"saml": {"properties": {"companyName": company}}, "oidc": {"applicationUrl": application_url}},
    }
    try:
        await service.update_application_section(app_id, "application_info", dict(payload))
        # on success trigger toast and redirect to detail page
        locale = get_request_locale(request)
        hx_trigger = {"toast": {"title": translate(locale, "toast.saved_title"), "body": translate(locale, "applications.detail.update_success"), "variant": "success"}, "redirect": f"/applications/{app_id}"}
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger), "HX-Redirect": f"/applications/{app_id}"})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/oidc-settings")
async def submit_oidc_settings(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    form = await request.form()
    redirect_text = str(form.get("redirectUris") or "").strip()
    redirect_uris = [line.strip() for line in redirect_text.splitlines() if line.strip()]
    require_pkce = True if form.get("requirePkceVerification") == "true" or form.get("requirePkceVerification") == "on" else False

    errors: dict = {}
    invalid_uris = [u for u in redirect_uris if not _is_valid_url(u)]
    if invalid_uris:
        errors["redirectUris"] = translate(get_request_locale(request), "validation.invalid_redirect_uris")
    if errors:
        context = {"request": request, "application_payload": {"providers": {"oidc": {"properties": {"redirectUris": redirect_uris}, "requirePkceVerification": require_pkce}}}, "app_id": app_id, "errors": errors}
        return _error_response(request, "fragments/oidc_settings_edit.html", context)

    payload = {"providers": {"oidc": {"properties": {"redirectUris": redirect_uris}, "requirePkceVerification": require_pkce}}}
    try:
        await service.update_application_section(app_id, "oidc_settings", payload)
        locale = get_request_locale(request)
        hx_trigger = {"toast": {"title": translate(locale, "toast.saved_title"), "body": translate(locale, "applications.detail.update_success"), "variant": "success"}, "redirect": f"/applications/{app_id}"}
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger), "HX-Redirect": f"/applications/{app_id}"})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/single-logout")
async def submit_single_logout(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    form = await request.form()
    logout_option = str(form.get("logoutOption") or "").strip()
    logout_uri = str(form.get("logoutURI") or "").strip()
    redirect_text = str(form.get("logoutRedirectURIs") or "").strip()
    redirect_uris = [line.strip() for line in redirect_text.splitlines() if line.strip()]

    errors: dict = {}
    if logout_option not in {"none", "frontchannel", "backchannel"}:
        errors["logoutOption"] = translate(get_request_locale(request), "validation.invalid_choice")
    if logout_uri and not _is_valid_url(logout_uri):
        errors["logoutURI"] = translate(get_request_locale(request), "validation.invalid_url")
    invalid_redirects = [u for u in redirect_uris if not _is_valid_url(u)]
    if invalid_redirects:
        errors["logoutRedirectURIs"] = translate(get_request_locale(request), "validation.invalid_redirect_uris")

    if errors:
        context = {"request": request, "application_payload": {"providers": {"oidc": {"properties": {"additionalConfig": {"logoutOption": logout_option, "logoutURI": logout_uri, "logoutRedirectURIs": redirect_uris}}}}}, "app_id": app_id, "errors": errors}
        return _error_response(request, "fragments/single_logout_edit.html", context)

    payload = {"providers": {"oidc": {"properties": {"additionalConfig": {"logoutOption": logout_option, "logoutURI": logout_uri, "logoutRedirectURIs": redirect_uris}}}}}
    try:
        await service.update_application_section(app_id, "single_logout", payload)
        locale = get_request_locale(request)
        hx_trigger = {"toast": {"title": translate(locale, "toast.saved_title"), "body": translate(locale, "applications.detail.update_success"), "variant": "success"}, "redirect": f"/applications/{app_id}"}
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger), "HX-Redirect": f"/applications/{app_id}"})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/people")
async def submit_people(request: Request, app_id: str, user: dict = Depends(require_web_user), service=Depends(get_admin_service)):
    form = await request.form()
    owners_text = str(form.get("owners") or "").strip()
    owners = [email.strip() for email in owners_text.splitlines() if email.strip()]

    errors: dict = {}
    invalid = [o for o in owners if not _is_valid_email(o)]
    if invalid:
        errors["owners"] = translate(get_request_locale(request), "validation.invalid_emails")
    if len(owners) > 50:
        errors["owners"] = translate(get_request_locale(request), "validation.too_many_items", max=50)

    if errors:
        context = {"request": request, "application_payload": {"owners": [{"email": o} for o in owners]}, "app_id": app_id, "errors": errors}
        return _error_response(request, "fragments/people_edit.html", context)

    payload = {"owners": [{"email": o} for o in owners]}
    try:
        await service.update_application_section(app_id, "people", payload)
        locale = get_request_locale(request)
        hx_trigger = {"toast": {"title": translate(locale, "toast.saved_title"), "body": translate(locale, "applications.detail.update_success"), "variant": "success"}, "redirect": f"/applications/{app_id}"}
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger), "HX-Redirect": f"/applications/{app_id}"})
    except NotImplementedError:
        return Response(status_code=501)
