from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from loguru import logger

from app.config import get_settings


class IBMVerifyUserClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient, access_token: str):
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._access_token = access_token

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def fetch_profile(self) -> Dict[str, Any]:
        response = await self._client.get(f"{self._base_url}/v2.0/Me", headers=self._auth_headers())
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {"profile": payload}

    async def fetch_userinfo(self) -> Dict[str, Any]:
        response = await self._client.get(
            f"{self._base_url}/oauth2/userinfo", headers=self._auth_headers()
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {"userinfo": payload}

    async def fetch_authenticators(self) -> Any:
        response = await self._client.get(
            f"{self._base_url}/v2.0/factors", headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()

    async def fetch_applications(self) -> Any:
        response = await self._client.get(
            f"{self._base_url}/v1.0/owner/applications",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        await self._client.aclose()


def _build_shared_user_http_client() -> httpx.AsyncClient:
    timeout = httpx.Timeout(5.0, read=10.0)
    return httpx.AsyncClient(timeout=timeout)


async def init_user_http_client(app: FastAPI) -> None:
    user_http_client = getattr(app.state, "user_http_client", None)
    if user_http_client is not None:
        return
    app.state.user_http_client = _build_shared_user_http_client()
    logger.info("Shared user HTTP client registered on app.state")


async def close_user_http_client(app: FastAPI) -> None:
    user_http_client = getattr(app.state, "user_http_client", None)
    if user_http_client is None:
        logger.info("No user_http_client found on app.state to close")
        return

    await user_http_client.aclose()
    logger.info("Closing shared user HTTP client")
    delattr(app.state, "user_http_client")


def get_user_http_client(request: Request) -> httpx.AsyncClient:
    user_http_client = getattr(request.app.state, "user_http_client", None)
    if user_http_client is None:
        raise ValueError("user_http_client is not initialized on app.state")
    return user_http_client


async def get_user_api_client(request: Request) -> IBMVerifyUserClient:
    settings = get_settings()
    session = getattr(request, "session", {}) or {}
    token = (session.get("tokens") or {}).get("access_token")
    if not token:
        accepts = request.headers.get("accept", "")
        if "text/html" in accepts and not request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/auth/login"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User access token missing from session",
        )

    http_client = get_user_http_client(request)

    return IBMVerifyUserClient(
        base_url=settings.ibm_sv_base_url,
        client=http_client,
        access_token=token,
    )
