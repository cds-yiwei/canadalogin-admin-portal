from pathlib import Path

import json
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.service.admin_service import AdminService
from app.dependencies.auth import require_web_user
from app.dependencies.services import get_admin_service
from app.controller.schemas import ClientSecretData, ClientSecretUpdatePayload
from app.utils.i18n import get_request_locale, register_i18n, translate

router = APIRouter(prefix="/fragments", tags=["fragments"])
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
register_i18n(templates)


@router.get("/requests", response_class=HTMLResponse)
async def requests_fragment(request: Request):
    pass


# Edit fragment GET handlers (application info, oidc settings, single logout, people)
@router.get("/application-info/edit", response_class=HTMLResponse)
async def fragment_application_info_edit(request: Request, app_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    modal_html = templates.get_template("fragments/application_info_edit_modal.html").render(
        request=request, application_payload=application, app_id=app_id
    )
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.get("/oidc-settings/edit", response_class=HTMLResponse)
async def fragment_oidc_settings_edit(request: Request, app_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    modal_html = templates.get_template("fragments/oidc_settings_edit_modal.html").render(request=request, application_payload=application, app_id=app_id)
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.get("/single-logout/edit", response_class=HTMLResponse)
async def fragment_single_logout_edit(request: Request, app_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    application_payload = application or {}
    logout_option = None
    try:
        logout_option = (
            application_payload.get("providers", {}).get("oidc", {}).get("properties", {}).get("additionalConfig", {}).get("logoutOption")
        )
    except Exception:
        logout_option = None
    modal_html = templates.get_template("fragments/single_logout_edit_modal.html").render(request=request, application_payload=application, app_id=app_id, logout_option=logout_option)
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.get("/people/edit", response_class=HTMLResponse)
async def fragment_people_edit(request: Request, app_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
    application = await service.get_application_detail(app_id)
    locale = get_request_locale(request)
    modal_html = templates.get_template("fragments/people_edit_modal.html").render(request=request, application_payload=application, app_id=app_id)
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})



    """Render the requests panel as an SSR island."""

    session = getattr(request, "session", {}) or {}
    user = session.get("user")
    return templates.TemplateResponse(
        request,
        "fragments/requests.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.get("/demo-modal", response_class=HTMLResponse)
async def demo_modal(request: Request):
    """Return HX-Trigger to open a demo modal form."""
    locale = get_request_locale(request)
    modal_html = """
        <div class='modal-panel' role='dialog' aria-modal='true'>
            <div class='modal-header' style='display:flex; align-items:center; gap:12px;'>
                <h3 class='modal-title'>{modal_title}</h3>
                <button class='modal-close' data-modal-close aria-label='Close'>×</button>
            </div>
            <div class='modal-body'>
                <form class='gcds-stack' style='gap:12px;' hx-post='/fragments/demo-modal/submit' hx-target='this' hx-swap='none'>
                    <label class='gcds-stack' style='gap:6px;'>
                        <span>{name_label}</span>
                        <input name='name' type='text' required class='gcds-input' placeholder='{name_placeholder}' />
                    </label>
                    <label class='gcds-stack' style='gap:6px;'>
                        <span>{message_label}</span>
                        <textarea name='message' rows='3' class='gcds-textarea' placeholder='{message_placeholder}'></textarea>
                    </label>
                    <div style='display:flex; gap:10px; justify-content:flex-end;'>
                        <button type='button' class='btn secondary' data-modal-close>{cancel_label}</button>
                        <button type='submit' class='btn'>{submit_label}</button>
                    </div>
                </form>
            </div>
        </div>
        """
    modal_html = modal_html.format(
        modal_title=translate(locale, "modal.title"),
        name_label=translate(locale, "modal.name_label"),
        message_label=translate(locale, "modal.message_label"),
        name_placeholder=translate(locale, "modal.name_placeholder"),
        message_placeholder=translate(locale, "modal.message_placeholder"),
        cancel_label=translate(locale, "modal.cancel"),
        submit_label=translate(locale, "modal.submit"),
    )
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.post("/demo-modal/submit", response_class=HTMLResponse)
async def demo_modal_submit(request: Request):
    """Handle demo modal form submission and close modal with a toast."""

    form = await request.form()
    name = str(form.get("name") or "there").strip()
    message = str(form.get("message") or "").strip()
    locale = get_request_locale(request)
    body = translate(locale, "toast.thanks", name=name)
    if message:
        body = f"{body} {translate(locale, 'toast.note_received', message=message)}"
    hx_trigger = {
        "closeModal": True,
        "toast": {
            "title": translate(locale, "toast.submitted_title"),
            "body": body,
            "variant": "success",
        },
    }
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.get("/demo-toast", response_class=HTMLResponse)
async def demo_toast(request: Request):
    """Simple endpoint that triggers a toast notification."""
    locale = get_request_locale(request)
    hx_trigger = {
        "toast": {
            "title": translate(locale, "toast.signed_in_title"),
            "body": translate(locale, "toast.welcome_back_demo"),
            "variant": "success",
        }
    }
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.get("/application-delete", response_class=HTMLResponse)
async def application_delete_modal(
    request: Request,
    app_id: str | None = None,
    app_name: str | None = None,
    client_id: str | None = None,
    _user: dict = Depends(require_web_user),
):
    locale = get_request_locale(request)
    if not app_id:
        hx_trigger = {
            "toast": {
                "title": translate(locale, "applications.detail.delete_error_title"),
                "body": translate(locale, "applications.detail.delete_error_body"),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    modal_html = templates.get_template("fragments/application_delete_modal.html").render(
        request=request,
        app_id=app_id,
        app_name=app_name,
        client_id=client_id,
    )
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.get("/client-secret", response_class=HTMLResponse)
async def client_secret_modal(
    request: Request,
    client_id: str | None = None,
    _user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    locale = get_request_locale(request)
    if not client_id:
        hx_trigger = {
            "toast": {
                "title": translate(locale, "applications.detail.client_secret_modal.missing_title"),
                "body": translate(locale, "applications.detail.client_secret_modal.missing_body"),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    secret_payload = await service.get_client_secret(client_id)
    if not isinstance(secret_payload, dict):
        secret_payload = {}

    secret_value = None
    rotated_secrets: list[dict] = []
    try:
        parsed = ClientSecretData.model_validate(secret_payload)
        secret_value = parsed.clientSecret
        rotated_secrets = [item.model_dump() for item in parsed.rotatedSecrets]
    except ValidationError:
        for key in (
            "clientSecret",
            "client_secret",
            "clientSecretValue",
            "secret",
            "value",
        ):
            candidate = secret_payload.get(key)
            if candidate:
                secret_value = candidate
                break
        raw_rotated = secret_payload.get("rotatedSecrets")
        if isinstance(raw_rotated, list):
            rotated_secrets = [item for item in raw_rotated if isinstance(item, dict)]

    modal_html = templates.get_template("fragments/client_secret_modal.html").render(
        request=request,
        client_id=client_id,
        client_secret=secret_value,
        client_secret_payload=secret_payload,
        rotated_secrets=rotated_secrets,
    )
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.get("/client-secret/edit", response_class=HTMLResponse)
async def client_secret_edit_modal(
    request: Request,
    client_id: str | None = None,
    _user: dict = Depends(require_web_user),
):
    locale = get_request_locale(request)
    if not client_id:
        hx_trigger = {
            "toast": {
                "title": translate(
                    locale, "applications.detail.client_secret_edit_modal.missing_title"
                ),
                "body": translate(
                    locale, "applications.detail.client_secret_edit_modal.missing_body"
                ),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    today = datetime.now().date()
    min_expiry_date = today.isoformat()
    max_expiry_date = (today + timedelta(days=89)).isoformat()

    modal_html = templates.get_template("fragments/client_secret_edit_modal.html").render(
        request=request,
        client_id=client_id,
        min_expiry_date=min_expiry_date,
        max_expiry_date=max_expiry_date,
    )
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.post("/client-secret/rotated/delete", response_class=HTMLResponse)
async def client_secret_rotated_delete(
    request: Request,
    _user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    form = await request.form()
    client_id = str(form.get("client_id") or "").strip()
    paths = [str(value) for value in form.getlist("path") if value]
    locale = get_request_locale(request)
    if not client_id:
        hx_trigger = {
            "toast": {
                "title": translate(locale, "applications.detail.client_secret_modal.missing_title"),
                "body": translate(locale, "applications.detail.client_secret_modal.missing_body"),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    if not paths:
        hx_trigger = {
            "toast": {
                "title": translate(
                    locale, "applications.detail.client_secret_modal.remove_missing_title"
                ),
                "body": translate(
                    locale, "applications.detail.client_secret_modal.remove_missing_body"
                ),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    try:
        await service.delete_rotated_client_secrets(client_id, paths)
    except Exception:  # noqa: BLE001
        hx_trigger = {
            "toast": {
                "title": translate(
                    locale, "applications.detail.client_secret_modal.remove_failed_title"
                ),
                "body": translate(
                    locale, "applications.detail.client_secret_modal.remove_failed_body"
                ),
                "variant": "danger",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    hx_trigger: dict[str, object] = {
        "closeModal": True,
        "toast": {
            "title": translate(
                locale,
                "applications.detail.client_secret_modal.remove_success_title",
            ),
            "body": translate(
                locale,
                "applications.detail.client_secret_modal.remove_success_body",
            ),
            "variant": "success",
        },
    }
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.post("/client-secret/edit", response_class=HTMLResponse)
async def client_secret_edit_submit(
    request: Request,
    _user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    form = await request.form()
    client_id = str(form.get("client_id") or "").strip()
    action = str(form.get("action") or "").strip()
    description = str(form.get("description") or "").strip()
    expire_date_raw = str(form.get("expire_date") or "").strip()
    locale = get_request_locale(request)

    if not client_id:
        hx_trigger = {
            "toast": {
                "title": translate(
                    locale, "applications.detail.client_secret_edit_modal.missing_title"
                ),
                "body": translate(
                    locale, "applications.detail.client_secret_edit_modal.missing_body"
                ),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    if action not in {"regenerate", "rotate"}:
        hx_trigger = {
            "toast": {
                "title": translate(
                    locale, "applications.detail.client_secret_edit_modal.invalid_action_title"
                ),
                "body": translate(
                    locale, "applications.detail.client_secret_edit_modal.invalid_action_body"
                ),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    rotated_secret_expired_at = 0

    if action == "rotate":
        if not description:
            hx_trigger = {
                "toast": {
                    "title": translate(
                        locale,
                        "applications.detail.client_secret_edit_modal.missing_description_title",
                    ),
                    "body": translate(
                        locale,
                        "applications.detail.client_secret_edit_modal.missing_description_body",
                    ),
                    "variant": "warning",
                }
            }
            return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

        if not expire_date_raw:
            hx_trigger = {
                "toast": {
                    "title": translate(
                        locale, "applications.detail.client_secret_edit_modal.missing_expiry_title"
                    ),
                    "body": translate(
                        locale, "applications.detail.client_secret_edit_modal.missing_expiry_body"
                    ),
                    "variant": "warning",
                }
            }
            return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

        try:
            parsed_date = date.fromisoformat(expire_date_raw)
        except ValueError:
            hx_trigger = {
                "toast": {
                    "title": translate(
                        locale, "applications.detail.client_secret_edit_modal.invalid_expiry_title"
                    ),
                    "body": translate(
                        locale, "applications.detail.client_secret_edit_modal.invalid_expiry_body"
                    ),
                    "variant": "warning",
                }
            }
            return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

        today = date.today()
        max_expiry_date = today + timedelta(days=89)
        if parsed_date <= today or parsed_date >= max_expiry_date:
            hx_trigger = {
                "toast": {
                    "title": translate(
                        locale, "applications.detail.client_secret_edit_modal.invalid_expiry_title"
                    ),
                    "body": translate(
                        locale, "applications.detail.client_secret_edit_modal.invalid_expiry_body"
                    ),
                    "variant": "warning",
                }
            }
            return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

        expire_dt = datetime.combine(parsed_date, time(23, 59, 59))
        rotated_secret_expired_at = int(expire_dt.timestamp())
    else:
        description = ""
        rotated_secret_expired_at = 0

    payload = ClientSecretUpdatePayload(
        deleteRotatedSecrets=False,
        description=description or "",
        rotatedSecretExpiredAt=rotated_secret_expired_at,
    ).model_dump()

    try:
        await service.update_client_secret(client_id, payload)
    except Exception:  # noqa: BLE001
        hx_trigger = {
            "toast": {
                "title": translate(
                    locale, "applications.detail.client_secret_edit_modal.submit_failed_title"
                ),
                "body": translate(
                    locale, "applications.detail.client_secret_edit_modal.submit_failed_body"
                ),
                "variant": "danger",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    success_key = (
        "applications.detail.client_secret_edit_modal.submit_success_regenerate"
        if action == "regenerate"
        else "applications.detail.client_secret_edit_modal.submit_success_rotate"
    )
    success_trigger: dict[str, object] = {
        "closeModal": True,
        "toast": {
            "title": translate(
                locale,
                "applications.detail.client_secret_edit_modal.submit_success_title",
            ),
            "body": translate(locale, success_key),
            "variant": "success",
        },
    }
    return Response("", headers={"HX-Trigger": json.dumps(success_trigger)})


@router.get("/add-owner-modal", response_class=HTMLResponse)
async def add_owner_modal(request: Request, _user: dict = Depends(require_web_user)):
    """Return the add owner modal fragment."""
    modal_html = templates.get_template("fragments/add_owner_modal.html").render(
        request=request,
    )
    hx_trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.post("/applications/{app_id}/edit/application-info", response_class=HTMLResponse)
async def submit_application_info(request: Request, app_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
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
        modal_html = templates.get_template("fragments/application_info_edit_modal.html").render(request=request, application_payload=context["application_payload"], app_id=app_id, errors=errors)
        return Response(modal_html, status_code=400)

    payload = {
        "name": name,
        "description": description,
        "providers": {"saml": {"properties": {"companyName": company}}, "oidc": {"applicationUrl": application_url}},
    }
    try:
        await service.update_application_section(app_id, "application_info", dict(payload))
        locale = get_request_locale(request)
        hx_trigger = {"toast": {"title": translate(locale, "toast.saved_title"), "body": translate(locale, "applications.detail.update_success"), "variant": "success"}, "redirect": f"/applications/{app_id}"}
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger), "HX-Redirect": f"/applications/{app_id}"})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/oidc-settings", response_class=HTMLResponse)
async def submit_oidc_settings(request: Request, app_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
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
        modal_html = templates.get_template("fragments/oidc_settings_edit_modal.html").render(request=request, application_payload=context["application_payload"], app_id=app_id, errors=errors)
        return Response(modal_html, status_code=400)

    payload = {"providers": {"oidc": {"properties": {"redirectUris": redirect_uris}, "requirePkceVerification": require_pkce}}}
    try:
        await service.update_application_section(app_id, "oidc_settings", payload)
        locale = get_request_locale(request)
        hx_trigger = {"toast": {"title": translate(locale, "toast.saved_title"), "body": translate(locale, "applications.detail.update_success"), "variant": "success"}, "redirect": f"/applications/{app_id}"}
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger), "HX-Redirect": f"/applications/{app_id}"})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/single-logout", response_class=HTMLResponse)
async def submit_single_logout(request: Request, app_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
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
        modal_html = templates.get_template("fragments/single_logout_edit_modal.html").render(request=request, application_payload=context["application_payload"], app_id=app_id, errors=errors, logout_option=logout_option)
        return Response(modal_html, status_code=400)

    payload = {"providers": {"oidc": {"properties": {"additionalConfig": {"logoutOption": logout_option, "logoutURI": logout_uri, "logoutRedirectURIs": redirect_uris}}}}}
    try:
        await service.update_application_section(app_id, "single_logout", payload)
        locale = get_request_locale(request)
        hx_trigger = {"toast": {"title": translate(locale, "toast.saved_title"), "body": translate(locale, "applications.detail.update_success"), "variant": "success"}, "redirect": f"/applications/{app_id}"}
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger), "HX-Redirect": f"/applications/{app_id}"})
    except NotImplementedError:
        return Response(status_code=501)


@router.post("/applications/{app_id}/edit/people", response_class=HTMLResponse)
async def submit_people(request: Request, app_id: str, _user: dict = Depends(require_web_user), service: AdminService = Depends(get_admin_service)):
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
        modal_html = templates.get_template("fragments/people_edit_modal.html").render(request=request, application_payload=context["application_payload"], app_id=app_id, errors=errors)
        return Response(modal_html, status_code=400)

    payload = {"owners": [{"email": o} for o in owners]}
    try:
        await service.update_application_section(app_id, "people", payload)
        locale = get_request_locale(request)
        hx_trigger = {"toast": {"title": translate(locale, "toast.saved_title"), "body": translate(locale, "applications.detail.update_success"), "variant": "success"}, "redirect": f"/applications/{app_id}"}
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger), "HX-Redirect": f"/applications/{app_id}"})
    except NotImplementedError:
        return Response(status_code=501)


@router.get("/{fragment_path:path}", response_class=HTMLResponse)
async def render_fragment(fragment_path: str, request: Request):
    """Fallback renderer for any other SSR islands."""

    return HTMLResponse("<!-- Fragment not found -->", status_code=404)
