from datetime import datetime, timedelta
from typing import Any, Dict, List

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import FastAPI, Request
from loguru import logger

from app.config import Settings


class IBMVerifyAdminClient:
    def __init__(self, base_url: str, client: AsyncOAuth2Client):
        self._base_url = base_url.rstrip("/")
        self._client = client

    async def fetch_users(self) -> List[Dict[str, Any]]:
        response = await self._client.get(f"{self._base_url}/v2.0/Users")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("Resources", [])

    async def list_applications(self) -> List[Dict[str, Any]]:
        response = await self._client.get(f"{self._base_url}/v1.0/applications")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("resources", payload.get("Resources", []))

    async def get_application_detail(self, application_id: str) -> Dict[str, Any]:
        response = await self._client.get(
            f"{self._base_url}/v1.0/applications/{application_id}"
        )
        response.raise_for_status()
        return response.json()

    async def create_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/v1.0/applications",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def delete_application(self, application_id: str) -> None:
        response = await self._client.delete(
            f"{self._base_url}/v1.0/applications/{application_id}"
        )
        response.raise_for_status()

    async def get_application_total_logins(
        self,
        application_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Dict[str, Any]:
        now = datetime.now()
        past_24_hours = now - timedelta(hours=24)
        to_timestamp = to_date or str(int(now.timestamp() * 1000))
        from_timestamp = from_date or str(int(past_24_hours.timestamp() * 1000))
        payload = {"APPID": application_id, "FROM": from_timestamp, "TO": to_timestamp}
        response = await self._client.post(
            f"{self._base_url}/v1.0/reports/app_total_logins",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_application_audit_trail(
        self,
        application_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
        size: int = 50,
        sort_by: str = "time",
        sort_order: str = "DESC",
    ) -> Dict[str, Any]:
        now = datetime.now()
        past_24_hours = now - timedelta(hours=24)
        to_timestamp = to_date or str(int(now.timestamp() * 1000))
        from_timestamp = from_date or str(int(past_24_hours.timestamp() * 1000))
        normalized_sort_order = (sort_order or "DESC").upper()
        if normalized_sort_order not in {"ASC", "DESC"}:
            normalized_sort_order = "DESC"
        payload = {
            "APPID": application_id,
            "FROM": from_timestamp,
            "TO": to_timestamp,
            "SIZE": size if size > 0 else 50,
            "SORT_BY": sort_by or "time",
            "SORT_ORDER": normalized_sort_order,
        }
        response = await self._client.post(
            f"{self._base_url}/v1.0/reports/app_audit_trail",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_client_secret(self, client_id: str) -> Dict[str, Any]:
        response = await self._client.get(
            f"{self._base_url}/oidc-mgmt/v2.0/clients/{client_id}/secrets"
        )
        response.raise_for_status()
        return response.json()

    async def update_client_secret(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/oidc-mgmt/v2.0/clients/{client_id}/secrets",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def delete_rotated_client_secrets(self, client_id: str, path: List[str]) -> bool:
        payload = [{"path": p, "op": "remove"} for p in path]
        response = await self._client.patch(
            f"{self._base_url}/oidc-mgmt/v2.0/clients/{client_id}/secrets",
            json=payload,
        )
        response.raise_for_status()
        return True

    async def get_application_entitlements(self, application_id: str) -> Dict[str, Any]:
        response = await self._client.get(
            f"{self._base_url}/v1.0/owner/applications/{application_id}/entitlements"
        )
        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        await self._client.aclose()


async def get_admin_api_client_async(request: Request) -> AsyncOAuth2Client:
    admin_api_client_async = getattr(request.app.state, "admin_api_client_async", None)
    if admin_api_client_async is None:
        raise ValueError("admin_api_client_async is not initialized on app.state")

    if not admin_api_client_async.token or admin_api_client_async.token.is_expired():
        logger.info("Fetching new token for Admin API client")
        await admin_api_client_async.fetch_token()
    return admin_api_client_async


async def init_admin_api_client(app: FastAPI, settings: Settings) -> None:
    """Initialize and register the admin API client during application startup."""
    token_endpoint = f"{settings.ibm_sv_base_url.rstrip('/')}/oauth2/token"
    admin_api_client_async = AsyncOAuth2Client(
        client_id=settings.ibm_sv_client_id,
        client_secret=settings.ibm_sv_client_secret,
        grant_type="client_credentials",
        token_endpoint=token_endpoint,
        leeway=120,
    )

    app.state.admin_api_client_async = admin_api_client_async
    logger.info("Async Admin API Client registered on app.state")


async def close_admin_api_client(app: FastAPI) -> None:
    """Close and unregister the admin API client during application shutdown."""
    admin_api_client_async = getattr(app.state, "admin_api_client_async", None)
    if admin_api_client_async is None:
        logger.info("No admin_api_client_async found on app.state to close")
        return

    await admin_api_client_async.aclose()
    logger.info("Closing Async Admin API Client")
    delattr(app.state, "admin_api_client_async")
