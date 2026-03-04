"""Web routes for group management (admin only)."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, Response
from loguru import logger
import json

from app.core.roles import Role
from app.service.admin_service import AdminService
from app.dependencies.auth import require_web_access
from app.dependencies.services import get_admin_service
from app.controller.web._utils import (
    templates,
    get_request_locale,
    translate,
)

router = APIRouter()


@router.get("/group-management/application-owners", response_class=HTMLResponse)
async def group_management_page(
    request: Request,
    user: dict = Depends(require_web_access(roles=[Role.SUPER_ADMIN])),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Display application owners group management page (SUPER_ADMIN only)."""
    locale = get_request_locale(request)

    try:
        # Find the "application owners" group
        groups = await admin_service.search_groups_by_name("application owners")
        if not groups:
            group_id = None
            members = []
        else:
            group_id = groups[0].get("id")
            group_detail = await admin_service.get_group_by_id(group_id)
            members = group_detail.get("members", [])
    except Exception as e:
        logger.error(f"Failed to fetch application owners group: {e}")
        members = []
        group_id = None

    return templates.TemplateResponse(
        request,
        "group_management/application_owners.html",
        {
            "request": request,
            "user": user,
            "group_id": group_id,
            "members": members,
            "title": "Application Owners Group Management",
            "breadcrumbs": [
                {"href": "/", "label": translate(locale, "breadcrumbs.dashboard")},
                {"href": "/group-management/application-owners", "label": "Group Management"},
            ],
        },
    )


@router.get("/fragments/group-member-remove-modal", response_class=HTMLResponse)
async def get_remove_member_modal(
    request: Request,
    member_id: str = None,
    member_email: str = None,
    user: dict = Depends(require_web_access(roles=[Role.SUPER_ADMIN])),
):
    """Get the remove member confirmation modal."""
    if not member_id:
        hx_trigger = {
            "toast": {
                "title": "Error",
                "body": "Member ID is required",
                "variant": "warning",
            }
        }
        return Response("", headers={"HX-Trigger": json.dumps(hx_trigger)})

    modal_html = templates.get_template("fragments/group_member_remove_modal.html").render(
        request=request,
        member_id=member_id,
        member_email=member_email,
    )
    hx_trigger = {"modal": {"html": modal_html}}
    # Return the modal HTML in the response body and also include HX-Trigger for compatibility
    return HTMLResponse(modal_html, headers={"HX-Trigger": json.dumps(hx_trigger)})


@router.post("/group-management/application-owners/add-user", response_class=HTMLResponse)
async def add_user_to_group(
    request: Request,
    user_id: str = None,
    user: dict = Depends(require_web_access(roles=[Role.SUPER_ADMIN])),
):
    """Add a user to the application owners group (HTMX handler).

    Acquire admin_service at runtime so tests that patch
    app.dependencies.services.get_admin_service are respected.
    """
    # Import get_admin_service at runtime to respect test patching
    import importlib

    services_mod = importlib.import_module("app.dependencies.services")
    get_admin_service_fn = getattr(services_mod, "get_admin_service")
    admin_service = get_admin_service_fn(request)
    if hasattr(admin_service, "__await__"):
        admin_service = await admin_service

    # Get user_id from form data or query params
    if not user_id:
        form_data = await request.form()
        user_id = form_data.get("user_id")

    if not user_id:
        return HTMLResponse(
            "<div style='color:#c00;'>Invalid user_id</div>",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Find the "application owners" group
        groups = await admin_service.search_groups_by_name("application owners")
        if not groups:
            return HTMLResponse(
                "<div style='color:#c00;'>Group not found</div>",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        group_id = groups[0].get("id")

        # Add user to group
        await admin_service.add_user_to_group(group_id, user_id)
        logger.info(f"User {user_id} added to application owners group")

        # Get the updated members list
        group_detail = await admin_service.get_group_by_id(group_id)
        members = group_detail.get("members", [])

        # Return updated members list with response to clear search
        response = templates.TemplateResponse(
            request,
            "fragments/group_members_list.html",
            {
                "request": request,
                "members": members,
                "group_id": group_id,
            },
        )
        # Add toast notification and instruct client to close modal via HX-Trigger (handled by base.html listener)
        response.headers["HX-Trigger"] = json.dumps(
            {
                "toast": {
                    "title": "User added successfully!",
                    "variant": "success",
                    "duration": 3000,
                },
                "closeModal": True,
            }
        )
        return response
    except Exception:
        # Log full exception for debugging
        logger.exception("Failed to add user to group")
        # Attempt to return the current members list to the client so UI stays in sync
        try:
            groups = await admin_service.search_groups_by_name("application owners")
            if not isinstance(groups, list):
                groups = []
            if groups:
                group_id = groups[0].get("id")
                group_detail = await admin_service.get_group_by_id(group_id)
                # Normalize group_detail into a dict-like structure
                if isinstance(group_detail, dict):
                    members = group_detail.get("members", [])
                else:
                    # Attempt attribute access then fallback to empty list
                    members_candidate = getattr(group_detail, "members", None)
                    if callable(members_candidate):
                        try:
                            members_candidate = members_candidate()
                        except Exception:
                            members_candidate = None
                    members = members_candidate if isinstance(members_candidate, list) else []
            else:
                members = []
        except Exception:
            members = []

        response = templates.TemplateResponse(
            request,
            "fragments/group_members_list.html",
            {
                "request": request,
                "members": members,
                "group_id": group_id if "group_id" in locals() else None,
            },
        )
        # Send an error toast and return 500 to indicate the operation failed.
        response.headers["HX-Trigger"] = json.dumps(
            {
                "toast": {
                    "title": "Failed to add user",
                    "body": "Unable to add user to group. See server logs.",
                    "variant": "danger",
                }
            }
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return response


@router.post("/group-management/application-owners/remove-user", response_class=HTMLResponse)
async def remove_user_from_group(
    request: Request,
    user_id: str = None,
    user: dict = Depends(require_web_access(roles=[Role.SUPER_ADMIN])),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Remove a user from the application owners group (HTMX handler)."""
    """Remove a user from the application owners group (HTMX handler)."""
    # Get user_id from form data or query params
    if not user_id:
        form_data = await request.form()
        user_id = form_data.get("user_id")

    if not user_id:
        return HTMLResponse(
            "<div style='color:#c00;'>Invalid user_id</div>",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Find the "application owners" group
        groups = await admin_service.search_groups_by_name("application owners")
        if not groups:
            return HTMLResponse(
                "<div style='color:#c00;'>Group not found</div>",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        group_id = groups[0].get("id")

        # Remove user from group
        await admin_service.remove_user_from_group(group_id, user_id)
        logger.info(f"User {user_id} removed from application owners group")

        # Return updated members list with toast notification
        group_detail = await admin_service.get_group_by_id(group_id)
        members = group_detail.get("members", [])

        response = templates.TemplateResponse(
            request,
            "fragments/group_members_list.html",
            {
                "request": request,
                "members": members,
                "group_id": group_id,
            },
        )
        # Add toast notification header
        response.headers["HX-Trigger"] = json.dumps(
            {
                "toast": {
                    "title": "User removed successfully!",
                    "variant": "success",
                    "duration": 3000,
                }
            }
        )
        return response
    except Exception as e:
        logger.error(f"Failed to remove user from group: {e}")
        return HTMLResponse(
            f"<div style='color:#c00;'>Error: {str(e)}</div>",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/group-management/application-owners/remove-user-modal", response_class=HTMLResponse)
async def remove_user_from_group_modal(
    request: Request,
    user_id: str = None,
    user: dict = Depends(require_web_access(roles=[Role.SUPER_ADMIN])),
):
    """Compatibility wrapper for older client code that posts to remove-user-modal.
    Acquire the admin_service at runtime from the services module so unit tests
    that patch app.dependencies.services.get_admin_service are respected.
    """
    # Import at runtime so tests can patch the symbol
    import importlib

    services_mod = importlib.import_module("app.dependencies.services")
    get_admin_service_fn = getattr(services_mod, "get_admin_service")
    # Call the possibly-patched function; it may be async
    admin_service = get_admin_service_fn(request)
    if hasattr(admin_service, "__await__"):
        admin_service = await admin_service
    return await remove_user_from_group(
        request, user_id=user_id, user=user, admin_service=admin_service
    )


@router.post("/api/v1/users/search", response_class=HTMLResponse)
async def search_users_html(
    request: Request,
    user: dict = Depends(require_web_access(roles=[Role.SUPER_ADMIN])),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Search users and return HTML fragment for HTMX (SUPER_ADMIN only)."""
    locale = get_request_locale(request)

    # Get username from form data (HTMX posts form data)
    form_data = await request.form()
    username = form_data.get("username", "").strip() if form_data else ""

    if not username:
        return HTMLResponse("<div></div>")  # Empty response on empty query

    try:
        # Search users via IBM Verify
        users = await admin_service.search_users_by_name(username)

        if not users:
            # No users returned by the backend search — show a friendly modal message
            msg = translate(locale, "group_management.search_no_results")
            logger.info(f"Search for '{username}' returned no users from admin_service")

            modal_html = f"""
            <div class=\"modal-panel gcds-card\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"search-modal-title\" style=\"padding:0; max-width:680px;\">
              <div class=\"modal-header\" style=\"padding:20px;\">
                <gcds-heading tag=\"h2\">{translate(locale, 'group_management.search_modal_title')}</gcds-heading>
                <button data-modal-close aria-label=\"Close\" style=\"background:none;border:none;font-size:24px;cursor:pointer;\">×</button>
              </div>
              <div class=\"modal-body\" style=\"padding:20px; text-align:center; color:#333;\">
                <gcds-text>{msg}</gcds-text>
              </div>
              <div class=\"modal-footer\" style=\"padding:12px 20px; gap:12px; display:flex; justify-content:flex-end;\">
                <gcds-button button-role=\"secondary\" data-modal-close>{translate(locale, 'group_management.button_cancel')}</gcds-button>
              </div>
            </div>
            """

            response = HTMLResponse(modal_html)
            response.headers["HX-Trigger"] = json.dumps({"modal": {"html": modal_html}})
            return response

        # Get current member IDs
        groups = await admin_service.search_groups_by_name("application owners")
        member_ids = set()
        if groups:
            group_id = groups[0].get("id")
            group_detail = await admin_service.get_group_by_id(group_id)
            members = group_detail.get("members", [])
            member_ids = {m.get("id") for m in members}

        # Filter out already added members
        filtered_users = [u for u in users if u.id not in member_ids]
        logger.info(
            f"search_users_html: username={username} users_found={len(users)} member_ids={len(member_ids)} filtered={len(filtered_users)}"
        )

        # Build HTML for results (inner list)
        add_label = translate(locale, "group_management.button_add")
        results_html = '<div style="border:1px solid #ccc; border-radius:4px; background:#fff;">'
        if not filtered_users:
            # No users available to add after filtering — show friendly message
            msg = translate(locale, "group_management.search_all_added")
            results_html += f'<div style="padding:20px; text-align:center; color:#333;"><gcds-text>{msg}</gcds-text></div>'
        else:
            for user in filtered_users:
                user_id = user.id
                user_email = user.email or user_id
                # Use Alpine-friendly close on success
                results_html += f"""
                <div style=\"padding:12px; border-bottom:1px solid #eee; display:flex; justify-content:space-between; align-items:center; gap:12px;\">
                  <div style=\"flex:1;\">
                    <div style=\"font-weight:600;\">{user_email}</div>
                  </div>
                  <form method=\"POST\" action=\"/group-management/application-owners/add-user\"
                        hx-post=\"/group-management/application-owners/add-user\"
                        hx-target=\"#members-list\"
                        hx-swap=\"innerHTML swap:1s\"
                        hx-on=\"htmx:afterRequest: if(event.detail && event.detail.xhr && event.detail.xhr.status >= 200 && event.detail.xhr.status < 300) {{ var el = document.getElementById('search-users-input'); if(el){{ el.value = ''; }} try {{ window.Alpine && Alpine.store && Alpine.store('ui') && Alpine.store('ui').closeModal && Alpine.store('ui').closeModal(); }} catch(e) {{}} }}\"
                        style=\"margin:0;\">
                    <input type=\"hidden\" name=\"user_id\" value=\"{user_id}\">
                    <gcds-button type=\"submit\" button-role=\"primary\" style=\"min-width:84px;\">{add_label}</gcds-button>
                  </form>
                </div>
                """
        results_html += "</div>"

        # Wrap results in a full modal HTML so HX-Trigger opens consistent modal
        modal_html = f"""
        <div class=\"modal-panel gcds-card\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"search-modal-title\" style=\"padding:0; max-width:680px;\">
          <div class=\"modal-header\" style=\"padding:20px;\">
            <gcds-heading tag=\"h2\">{translate(locale, 'group_management.search_modal_title')}</gcds-heading>
            <button data-modal-close aria-label=\"Close\" style=\"background:none;border:none;font-size:24px;cursor:pointer;\">×</button>
          </div>
          <div class=\"modal-body\" style=\"padding:12px 20px; gap:12px; display:flex; flex-direction:column;\">
            {results_html}
          </div>
          <div class=\"modal-footer\" style=\"padding:12px 20px; gap:12px; display:flex; justify-content:flex-end;\">
            <gcds-button button-role=\"secondary\" data-modal-close>{translate(locale, 'group_management.button_cancel')}</gcds-button>
          </div>
        </div>
        """

        response = HTMLResponse(modal_html)
        # Trigger client to open modal via HX-Trigger event (use standard modal payload)
        response.headers["HX-Trigger"] = json.dumps({"modal": {"html": modal_html}})
        return response
    except Exception as e:
        logger.error(f"Search failed: {e}")
        error_msg = translate(locale, "group_management.search_error")
        return HTMLResponse(
            f'<div style="padding:12px; color:#c00;"><gcds-text>{error_msg}</gcds-text></div>',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
