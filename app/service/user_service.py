from typing import Any, Dict

from app.repository.iv_user_client import IBMVerifyUserClient


class UserService:
    def __init__(self, client: IBMVerifyUserClient):
        self._client = client

    async def get_profile(self) -> Dict[str, Any]:
        return await self._client.fetch_profile()

    async def get_userinfo(self) -> Dict[str, Any]:
        return await self._client.fetch_userinfo()

    async def get_authenticators(self) -> Any:
        return await self._client.fetch_authenticators()

    async def get_applications(self) -> Any:
        return await self._client.fetch_applications()
