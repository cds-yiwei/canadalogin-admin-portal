from __future__ import annotations

from fastapi import Request

from app.service.admin_service import AdminService
from app.service.user_service import UserService
from app.config import get_settings
from app.repository.iv_admin_client import IBMVerifyAdminClient, get_admin_api_client_async
from app.repository.iv_user_client import get_user_api_client


async def get_admin_service(request: Request) -> AdminService:
    settings = get_settings()
    client = await get_admin_api_client_async(request)
    gateway = IBMVerifyAdminClient(base_url=settings.ibm_sv_base_url, client=client)
    return AdminService(gateway)


async def get_user_service(request: Request) -> UserService:
    gateway = await get_user_api_client(request)
    return UserService(gateway)
