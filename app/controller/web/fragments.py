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
    """Render the requests panel as an SSR island."""

    session = getattr(request, "session", {}) or {}
    user = session.get("user")
    return templates.TemplateResponse(
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
    trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(trigger)})


@router.post("/demo-modal/submit", response_class=HTMLResponse)
async def demo_modal_submit(request: Request):
    """Handle demo modal form submission and close modal with a toast."""

    form = await request.form()
    name = (form.get("name") or "there").strip()
    message = (form.get("message") or "").strip()
    locale = get_request_locale(request)
    body = translate(locale, "toast.thanks", name=name)
    if message:
        body = f"{body} {translate(locale, 'toast.note_received', message=message)}"
    trigger = {
        "closeModal": True,
        "toast": {
            "title": translate(locale, "toast.submitted_title"),
            "body": body,
            "variant": "success",
        },
    }
    return Response("", headers={"HX-Trigger": json.dumps(trigger)})


@router.get("/demo-toast", response_class=HTMLResponse)
async def demo_toast(request: Request):
    """Simple endpoint that triggers a toast notification."""
    locale = get_request_locale(request)
    trigger = {
        "toast": {
            "title": translate(locale, "toast.signed_in_title"),
            "body": translate(locale, "toast.welcome_back_demo"),
            "variant": "success",
        }
    }
    return Response("", headers={"HX-Trigger": json.dumps(trigger)})


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
        trigger = {
            "toast": {
                "title": translate(locale, "applications.detail.delete_error_title"),
                "body": translate(locale, "applications.detail.delete_error_body"),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

    modal_html = templates.get_template("fragments/application_delete_modal.html").render(
        request=request,
        app_id=app_id,
        app_name=app_name,
        client_id=client_id,
    )
    trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(trigger)})


@router.get("/client-secret", response_class=HTMLResponse)
async def client_secret_modal(
    request: Request,
    client_id: str | None = None,
    _user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    locale = get_request_locale(request)
    if not client_id:
        trigger = {
            "toast": {
                "title": translate(locale, "applications.detail.client_secret_modal.missing_title"),
                "body": translate(locale, "applications.detail.client_secret_modal.missing_body"),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

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
    trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(trigger)})


@router.get("/client-secret/edit", response_class=HTMLResponse)
async def client_secret_edit_modal(
    request: Request,
    client_id: str | None = None,
    _user: dict = Depends(require_web_user),
):
    locale = get_request_locale(request)
    if not client_id:
        trigger = {
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
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

    today = datetime.now().date()
    min_expiry_date = today.isoformat()
    max_expiry_date = (today + timedelta(days=89)).isoformat()

    modal_html = templates.get_template("fragments/client_secret_edit_modal.html").render(
        request=request,
        client_id=client_id,
        min_expiry_date=min_expiry_date,
        max_expiry_date=max_expiry_date,
    )
    trigger = {"modal": {"html": modal_html}}
    return Response("", headers={"HX-Trigger": json.dumps(trigger)})


@router.post("/client-secret/rotated/delete", response_class=HTMLResponse)
async def client_secret_rotated_delete(
    request: Request,
    _user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    form = await request.form()
    client_id = (form.get("client_id") or "").strip()
    paths = [value for value in form.getlist("path") if value]
    locale = get_request_locale(request)

    if not client_id:
        trigger = {
            "toast": {
                "title": translate(locale, "applications.detail.client_secret_modal.missing_title"),
                "body": translate(locale, "applications.detail.client_secret_modal.missing_body"),
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

    if not paths:
        trigger = {
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
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

    try:
        await service.delete_rotated_client_secrets(client_id, paths)
    except Exception:  # noqa: BLE001
        trigger = {
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
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

    trigger = {
        "closeModal": True,
        "toast": {
            "title": translate(
                locale, "applications.detail.client_secret_modal.remove_success_title"
            ),
            "body": translate(
                locale, "applications.detail.client_secret_modal.remove_success_body"
            ),
            "variant": "success",
        },
    }
    return Response("", headers={"HX-Trigger": json.dumps(trigger)})


@router.post("/client-secret/edit", response_class=HTMLResponse)
async def client_secret_edit_submit(
    request: Request,
    _user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    form = await request.form()
    client_id = (form.get("client_id") or "").strip()
    action = (form.get("action") or "").strip()
    description = (form.get("description") or "").strip()
    expire_date_raw = (form.get("expire_date") or "").strip()
    locale = get_request_locale(request)

    if not client_id:
        trigger = {
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
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

    if action not in {"regenerate", "rotate"}:
        trigger = {
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
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

    rotated_secret_expired_at = 0

    if action == "rotate":
        if not description:
            trigger = {
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
            return Response("", headers={"HX-Trigger": json.dumps(trigger)})

        if not expire_date_raw:
            trigger = {
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
            return Response("", headers={"HX-Trigger": json.dumps(trigger)})

        try:
            parsed_date = date.fromisoformat(expire_date_raw)
        except ValueError:
            trigger = {
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
            return Response("", headers={"HX-Trigger": json.dumps(trigger)})

        today = date.today()
        max_expiry_date = today + timedelta(days=89)
        if parsed_date <= today or parsed_date >= max_expiry_date:
            trigger = {
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
            return Response("", headers={"HX-Trigger": json.dumps(trigger)})

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
        trigger = {
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
        return Response("", headers={"HX-Trigger": json.dumps(trigger)})

    success_key = (
        "applications.detail.client_secret_edit_modal.submit_success_regenerate"
        if action == "regenerate"
        else "applications.detail.client_secret_edit_modal.submit_success_rotate"
    )
    trigger = {
        "closeModal": True,
        "toast": {
            "title": translate(
                locale, "applications.detail.client_secret_edit_modal.submit_success_title"
            ),
            "body": translate(locale, success_key),
            "variant": "success",
        },
    }
    return Response("", headers={"HX-Trigger": json.dumps(trigger)})


@router.get("/{fragment_path:path}", response_class=HTMLResponse)
async def render_fragment(fragment_path: str, request: Request):
    """Fallback renderer for any other SSR islands."""

    return HTMLResponse("<!-- Fragment not found -->", status_code=404)
