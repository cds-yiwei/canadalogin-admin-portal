from typing import Any, Dict, List, Optional

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
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._client.get_application_total_logins(application_id, from_date, to_date)

    async def get_application_audit_trail(
        self,
        application_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
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

    async def get_application_audit_trail_search_after(
        self,
        application_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        size: int = 25,
        search_after: Optional[str] = None,
        search_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call repository search_after API and normalize results.

        Returns: dict {"events": [...], "next": str|None, "prev": str|None}
        """
        raw = await self._client.app_audit_trail_search_after(
            application_id,
            from_date,
            to_date,
            size=size,
            search_after=search_after,
            search_dir=search_dir,
        )
        # raw expected to be dict with 'events' and optional 'next'/'prev'
        events = []
        next_token = None
        prev_token = None
        if isinstance(raw, dict):
            events = raw.get("events") or []
            next_token = raw.get("next")
            prev_token = raw.get("prev")
        elif raw and isinstance(raw, (list, tuple)):
            # backward-compatible: if client returned tuple (events, tokens)
            try:
                events = raw[0] or []
                tokens = raw[1] if len(raw) > 1 else {}
                next_token = tokens.get("next") if isinstance(tokens, dict) else None
                prev_token = tokens.get("prev") if isinstance(tokens, dict) else None
            except Exception:
                events = []
        # Normalize into consistent dict shape
        return {"events": events, "next": next_token, "prev": prev_token}

    async def get_client_secret(self, client_id: str) -> Dict[str, Any]:
        return await self._client.get_client_secret(client_id)

    async def update_client_secret(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._client.update_client_secret(client_id, payload)

    async def delete_rotated_client_secrets(self, client_id: str, path: List[str]) -> bool:
        return await self._client.delete_rotated_client_secrets(client_id, path)

    async def get_application_entitlements(self, application_id: str) -> Dict[str, Any]:
        return await self._client.get_application_entitlements(application_id)

    async def list_groups(self, count: int = 100, start_index: int = 1) -> List[Dict[str, Any]]:
        """List all groups."""
        return await self._client.list_groups(count, start_index)

    async def search_groups_by_name(self, group_name: str) -> List[Dict[str, Any]]:
        """Search for groups by name."""
        return await self._client.search_groups_by_name(group_name)

    async def get_group_by_id(self, group_id: str) -> Dict[str, Any]:
        """Get a specific group by ID."""
        return await self._client.get_group_by_id(group_id)

    async def add_user_to_group(self, group_id: str, user_id: str) -> None:
        """Add a user to a group."""
        await self._client.add_user_to_group(group_id, user_id)

    async def remove_user_from_group(self, group_id: str, user_id: str) -> None:
        """Remove a user from a group."""
        await self._client.remove_user_from_group(group_id, user_id)

    async def is_user_in_group(self, group_id: str, user_id: str) -> bool:
        """Check if a user is a member of a group."""
        return await self._client.is_user_in_group(group_id, user_id)
