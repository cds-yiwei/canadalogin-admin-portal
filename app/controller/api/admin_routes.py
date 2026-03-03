import json
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.service.admin_service import AdminService
from app.controller.schemas import (
    ApplicationAuditTrailResponse,
    ApplicationDetailData,
    ApplicationEntitlementsResponse,
    ApplicationTotalLoginsResponse,
    ClientSecretResponse,
    UserRead,
)
from app.controller._utils import (
    _build_application_creation_payload,
    _extract_application_id,
)
from app.core.roles import Role
from app.dependencies.auth import require_api_access, require_web_user
from app.dependencies.services import get_admin_service
from app.repository.exceptions import IBMVerifyBadRequest
from loguru import logger

router = APIRouter()


@router.get("/health")
async def healthcheck():
    return {"status": "ok"}


@router.post("/applications")
async def create_application(
    request: Request,
    _user: dict = Depends(require_web_user),
    service: AdminService = Depends(get_admin_service),
):
    """Create a new application via API.

    Returns 201 on success with application data.
    Returns 400 on validation error with error detail.
    """
    form_data = await request.form()
    owner_id = (_user or {}).get("id")
    owners: list[str] = [owner_id] if owner_id else []

    # Parse owners from hidden JSON field or form list
    owners_value = form_data.get("owners")
    if owners_value:
        # Try to parse as JSON array first
        if isinstance(owners_value, str) and owners_value.startswith("["):
            try:
                owner_ids = json.loads(owners_value)
                for owner_id_item in owner_ids:
                    owner_id_str = str(owner_id_item).strip()
                    if owner_id_str and owner_id_str not in owners:
                        owners.append(owner_id_str)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to parse owners JSON: {}", e)
        # If not JSON, treat as single string value (don't fall through to getlist)
        elif isinstance(owners_value, str) and owners_value not in owners:
            owners.append(owners_value.strip())

    try:
        payload = _build_application_creation_payload(dict(form_data), owners)
        created = await service.create_application(payload)
        created_id = _extract_application_id(created)

        return JSONResponse(
            {"id": created_id or "", "data": created},
            status_code=status.HTTP_201_CREATED,
        )
    except IBMVerifyBadRequest as exc:
        error_detail = exc.get_error_detail()
        logger.warning("Application creation validation failed: {}", error_detail)
        return JSONResponse(
            {"detail": error_detail},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except ValueError as exc:
        error_msg = str(exc)
        logger.warning("Application creation validation error: {}", error_msg)
        return JSONResponse(
            {"detail": error_msg},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Application creation failed: {}", exc)
        return JSONResponse(
            {"detail": "Internal server error during application creation"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/users", response_model=list[UserRead])
async def list_users(
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    return [UserRead.model_validate(user) for user in await service.list_users()]


@router.get("/users/search", response_model=list[UserRead])
async def search_users(
    username: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    return [UserRead.model_validate(user) for user in await service.search_users_by_name(username)]


@router.get(
    "/applications/{application_id}/entitlements", response_model=ApplicationEntitlementsResponse
)
async def get_application_entitlements(
    application_id: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    data = await service.get_application_entitlements(application_id)
    return ApplicationEntitlementsResponse.model_validate(data)


@router.get(
    "/applications/{application_id}/reports/total-logins",
    response_model=ApplicationTotalLoginsResponse,
)
async def get_application_total_logins(
    application_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    data = await service.get_application_total_logins(application_id, from_date, to_date)
    return ApplicationTotalLoginsResponse.model_validate(data)


@router.get(
    "/applications/{application_id}/reports/audit-trail",
    response_model=ApplicationAuditTrailResponse,
)
async def get_application_audit_trail(
    application_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    size: int = 50,
    sort_by: str = "time",
    sort_order: str = "DESC",
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    data = await service.get_application_audit_trail(
        application_id, from_date, to_date, size, sort_by, sort_order
    )
    return ApplicationAuditTrailResponse.model_validate(data)


@router.get("/applications/{application_id}", response_model=ApplicationDetailData)
async def get_application_detail(
    application_id: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    data = await service.get_application_detail(application_id)
    return ApplicationDetailData.model_validate(data)


@router.get("/clients/{client_id}/secrets", response_model=ClientSecretResponse)
async def get_client_secret(
    client_id: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    data = await service.get_client_secret(client_id)
    return ClientSecretResponse.model_validate(data)


@router.get("/groups")
async def list_groups(
    count: int = 100,
    start_index: int = 1,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    """List all groups."""
    return await service.list_groups(count, start_index)


@router.get("/groups/search")
async def search_groups(
    group_name: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    """Search for groups by name."""
    return await service.search_groups_by_name(group_name)


@router.get("/groups/{group_id}")
async def get_group(
    group_id: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    """Get a specific group by ID."""
    return await service.get_group_by_id(group_id)


@router.post("/groups/{group_id}/members/{user_id}")
async def add_user_to_group(
    group_id: str,
    user_id: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    """Add a user to a group."""
    await service.add_user_to_group(group_id, user_id)
    return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK)


@router.delete("/groups/{group_id}/members/{user_id}")
async def remove_user_from_group(
    group_id: str,
    user_id: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    """Remove a user from a group."""
    await service.remove_user_from_group(group_id, user_id)
    return JSONResponse({"status": "success"}, status_code=status.HTTP_204_NO_CONTENT)


@router.get("/groups/{group_id}/members/{user_id}")
async def check_user_in_group(
    group_id: str,
    user_id: str,
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    """Check if a user is a member of a group."""
    is_member = await service.is_user_in_group(group_id, user_id)
    return JSONResponse({"is_member": is_member}, status_code=status.HTTP_200_OK)
