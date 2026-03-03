from __future__ import annotations

from app.core.permissions import ALL_PERMISSIONS
from app.core.roles import Role
from app.repository.yaml_role_policy_repository import YamlRolePolicyRepository


class AuthorizationService:
    def __init__(self, policy_repository: YamlRolePolicyRepository):
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
