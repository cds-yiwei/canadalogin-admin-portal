from typing import Any, Dict, List, Protocol
from app.core.models.user import User
from app.core.roles import Role


class AdminGateway(Protocol):
    async def fetch_users(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def get_application_detail(self, application_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def create_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def delete_application(self, application_id: str) -> None:
        raise NotImplementedError

    async def get_application_total_logins(
        self,
        application_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_application_audit_trail(
        self,
        application_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
        size: int = 50,
        sort_by: str = "time",
        sort_order: str = "DESC",
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_client_secret(self, client_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def update_client_secret(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def delete_rotated_client_secrets(self, client_id: str, path: List[str]) -> bool:
        raise NotImplementedError

    async def get_application_entitlements(self, application_id: str) -> Dict[str, Any]:
        raise NotImplementedError


class AdminService:
    def __init__(self, gateway: AdminGateway):
        self._gateway = gateway

    async def list_users(self) -> List[User]:
        data = await self._gateway.fetch_users()
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
        return await self._gateway.get_application_detail(application_id)

    async def create_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._gateway.create_application(payload)

    async def delete_application(self, application_id: str) -> None:
        await self._gateway.delete_application(application_id)

    async def get_application_total_logins(
        self,
        application_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Dict[str, Any]:
        return await self._gateway.get_application_total_logins(application_id, from_date, to_date)

    async def get_application_audit_trail(
        self,
        application_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
        size: int = 50,
        sort_by: str = "time",
        sort_order: str = "DESC",
    ) -> Dict[str, Any]:
        return await self._gateway.get_application_audit_trail(
            application_id,
            from_date,
            to_date,
            size,
            sort_by,
            sort_order,
        )

    async def get_client_secret(self, client_id: str) -> Dict[str, Any]:
        return await self._gateway.get_client_secret(client_id)

    async def update_client_secret(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._gateway.update_client_secret(client_id, payload)

    async def delete_rotated_client_secrets(self, client_id: str, path: List[str]) -> bool:
        return await self._gateway.delete_rotated_client_secrets(client_id, path)

    async def get_application_entitlements(self, application_id: str) -> Dict[str, Any]:
        return await self._gateway.get_application_entitlements(application_id)
