from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.service.authorization_service import AuthorizationService
from app.repository.yaml_role_policy_repository import YamlRolePolicyRepository

APP_DIR = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _get_role_policy_repository() -> YamlRolePolicyRepository:
    policy_path = APP_DIR / "policies" / "roles.yaml"
    return YamlRolePolicyRepository(policy_path)


def get_authorization_service() -> AuthorizationService:
    return AuthorizationService(_get_role_policy_repository())
