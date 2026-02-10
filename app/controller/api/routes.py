from fastapi import APIRouter, Depends

from app.service.admin_service import AdminService
from app.service.user_service import UserService
from app.controller.schemas import (
    ApplicationAuditTrailResponse,
    ApplicationDetailData,
    ApplicationEntitlementsResponse,
    ApplicationTotalLoginsResponse,
    ClientSecretResponse,
    ProfileResponse,
    UserRead,
)
from app.core.roles import Role
from app.dependencies.auth import require_api_access, require_api_user
from app.dependencies.services import get_admin_service, get_user_service

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def healthcheck():
    return {"status": "ok"}


@router.get("/users", response_model=list[UserRead])
async def list_users(
    _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])),
    service: AdminService = Depends(get_admin_service),
):
    return [UserRead.model_validate(user) for user in await service.list_users()]


@router.get("/me", response_model=ProfileResponse)
async def get_current_user_profile(
    _user: dict = Depends(require_api_user),
    service: UserService = Depends(get_user_service),
):
    profile = await service.get_profile()
    return ProfileResponse.model_validate(profile)


@router.get("/applications/{application_id}/entitlements", response_model=ApplicationEntitlementsResponse)
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
        application_id,
        from_date,
        to_date,
        size,
        sort_by,
        sort_order,
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
