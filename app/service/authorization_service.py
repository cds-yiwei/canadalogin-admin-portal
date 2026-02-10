from __future__ import annotations

from typing import Dict, List, Protocol
from app.core.permissions import ALL_PERMISSIONS
from app.core.roles import Role


class AuthorizationService:
    def __init__(self, policy_repository: RolePolicyRepository):
        self._policy_repository = policy_repository

    def resolve_permissions(self, roles: list[Role]) -> list[str]:
        policy = self._policy_repository.load_policy()
        resolved = set()
        for role in roles:
            for perm in policy.get(role.value, []):
                if perm == "*":
                    resolved.update(ALL_PERMISSIONS)
                    break
                resolved.add(perm)
        return sorted(resolved)


class RolePolicyRepository(Protocol):
    def load_policy(self) -> Dict[str, List[str]]:
        raise NotImplementedError
