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
    ProfileResponse,
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
    for value in form_data.getlist("owners"):
        owner_value = str(value).strip()
        if owner_value and owner_value not in owners:
            owners.append(owner_value)

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
async def list_users(_user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])), service: AdminService = Depends(get_admin_service)):
    return [UserRead.model_validate(user) for user in await service.list_users()]


@router.get("/applications/{application_id}/entitlements", response_model=ApplicationEntitlementsResponse)
async def get_application_entitlements(application_id: str, _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])), service: AdminService = Depends(get_admin_service)):
    data = await service.get_application_entitlements(application_id)
    return ApplicationEntitlementsResponse.model_validate(data)


@router.get("/applications/{application_id}/reports/total-logins", response_model=ApplicationTotalLoginsResponse)
async def get_application_total_logins(application_id: str, from_date: str | None = None, to_date: str | None = None, _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])), service: AdminService = Depends(get_admin_service)):
    data = await service.get_application_total_logins(application_id, from_date, to_date)
    return ApplicationTotalLoginsResponse.model_validate(data)


@router.get("/applications/{application_id}/reports/audit-trail", response_model=ApplicationAuditTrailResponse)
async def get_application_audit_trail(application_id: str, from_date: str | None = None, to_date: str | None = None, size: int = 50, sort_by: str = "time", sort_order: str = "DESC", _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])), service: AdminService = Depends(get_admin_service)):
    data = await service.get_application_audit_trail(application_id, from_date, to_date, size, sort_by, sort_order)
    return ApplicationAuditTrailResponse.model_validate(data)


@router.get("/applications/{application_id}", response_model=ApplicationDetailData)
async def get_application_detail(application_id: str, _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])), service: AdminService = Depends(get_admin_service)):
    data = await service.get_application_detail(application_id)
    return ApplicationDetailData.model_validate(data)


@router.get("/clients/{client_id}/secrets", response_model=ClientSecretResponse)
async def get_client_secret(client_id: str, _user: dict = Depends(require_api_access(roles=[Role.SUPER_ADMIN])), service: AdminService = Depends(get_admin_service)):
    data = await service.get_client_secret(client_id)
    return ClientSecretResponse.model_validate(data)
