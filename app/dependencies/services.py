from __future__ import annotations

from fastapi import Request

from app.service.admin_service import AdminService
from app.service.user_service import UserService
from app.config import get_settings
from app.repository.iv_admin_client import IBMVerifyAdminClient, get_admin_api_client_async
from app.repository.iv_user_client import get_user_api_client


async def get_admin_service(request: Request) -> AdminService:
    # Allow test-time patching of this dependency by delegating to the module-level
    # attribute if it has been replaced. This lets tests patch
    # "app.dependencies.services.get_admin_service" after app creation and have
    # the patched callable honored at request time.
    import sys

    mod = sys.modules[__name__]
    current = getattr(mod, "get_admin_service")
    if current is not get_admin_service:
        result = current(request)
        if hasattr(result, "__await__"):
            return await result
        return result

    settings = get_settings()
    client = await get_admin_api_client_async(request)
    admin_client = IBMVerifyAdminClient(base_url=settings.ibm_sv_base_url, client=client)
    return AdminService(admin_client)


async def get_user_service(request: Request) -> UserService:
    user_client = await get_user_api_client(request)
    return UserService(user_client)
