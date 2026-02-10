from typing import Any, Dict, Protocol


class UserGateway(Protocol):
    async def fetch_profile(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def fetch_userinfo(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def fetch_authenticators(self) -> Any:
        raise NotImplementedError

    async def fetch_applications(self) -> Any:
        raise NotImplementedError


class UserService:
    def __init__(self, gateway: UserGateway):
        self._gateway = gateway

    async def get_profile(self) -> Dict[str, Any]:
        return await self._gateway.fetch_profile()

    async def get_userinfo(self) -> Dict[str, Any]:
        return await self._gateway.fetch_userinfo()

    async def get_authenticators(self) -> Any:
        return await self._gateway.fetch_authenticators()

    async def get_applications(self) -> Any:
        return await self._gateway.fetch_applications()
