from typing import Any, Dict, List

from app.core.models.user import User
from app.core.roles import Role
from app.repository.iv_admin_client import IBMVerifyAdminClient


class AdminService:
    def __init__(self, client: IBMVerifyAdminClient):
        self._client = client

    async def list_users(self) -> List[User]:
        data = await self._client.fetch_users()
        return [
            User(
                id=item.get("id", "unknown"),
                email=item.get("userName", ""),
                roles=[Role.READ_ONLY],
                permissions=item.get("permissions", []),
            )
            for item in data
        ]

    async def search_users_by_name(self, username: str) -> List[User]:
        """Search for users by username."""
        data = await self._client.search_users_by_name(username)
        return [
            User(
                id=item.get("id", "unknown"),
                email=item.get("userName", ""),
                roles=[Role.READ_ONLY],
                permissions=item.get("permissions", []),
            )
            for item in data
        ]

    async def get_application_detail(self, application_id: str) -> Dict[str, Any]:
        return await self._client.get_application_detail(application_id)

    async def create_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._client.create_application(payload)

    async def delete_application(self, application_id: str) -> None:
        await self._client.delete_application(application_id)

    async def get_application_total_logins(
        self,
        application_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Dict[str, Any]:
        return await self._client.get_application_total_logins(application_id, from_date, to_date)

    async def get_application_audit_trail(
        self,
        application_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
        size: int = 50,
        sort_by: str = "time",
        sort_order: str = "DESC",
    ) -> Dict[str, Any]:
        return await self._client.get_application_audit_trail(
            application_id,
            from_date,
            to_date,
            size,
            sort_by,
            sort_order,
        )

    async def get_client_secret(self, client_id: str) -> Dict[str, Any]:
        return await self._client.get_client_secret(client_id)

    async def update_client_secret(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._client.update_client_secret(client_id, payload)

    async def delete_rotated_client_secrets(self, client_id: str, path: List[str]) -> bool:
        return await self._client.delete_rotated_client_secrets(client_id, path)

    async def get_application_entitlements(self, application_id: str) -> Dict[str, Any]:
        return await self._client.get_application_entitlements(application_id)
