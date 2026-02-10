from __future__ import annotations

from typing import Iterable, Optional, Sequence

from fastapi import HTTPException, Request, status

from app.core.roles import Role


def _get_session_user(request: Request) -> Optional[dict]:
    session = getattr(request, "session", {}) or {}
    return session.get("user")


def _normalize_roles(roles: Optional[Sequence[Role | str]]) -> set[str]:
    if not roles:
        return set()
    normalized = set()
    for role in roles:
        if isinstance(role, Role):
            normalized.add(role.value)
        else:
            normalized.add(str(role))
    return normalized


def _normalize_permissions(permissions: Optional[Iterable[str]]) -> set[str]:
    if not permissions:
        return set()
    return {str(perm) for perm in permissions}


def _is_authorized(
    user: dict,
    roles: Optional[Sequence[Role | str]],
    permissions: Optional[Iterable[str]],
) -> bool:
    required_roles = _normalize_roles(roles)
    required_permissions = _normalize_permissions(permissions)
    if not required_roles and not required_permissions:
        return True

    user_roles = set(user.get("roles") or [])
    user_permissions = set(user.get("permissions") or [])
    has_role = bool(required_roles and user_roles.intersection(required_roles))
    has_permission = bool(
        required_permissions and user_permissions.intersection(required_permissions)
    )
    return has_role or has_permission


def require_web_access(
    *,
    roles: Optional[Sequence[Role | str]] = None,
    permissions: Optional[Iterable[str]] = None,
):
    async def dependency(request: Request) -> dict:
        user = _get_session_user(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": "/auth/login"},
            )
        if not _is_authorized(user, roles, permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return user

    return dependency


async def require_web_user(request: Request) -> dict:
    return await require_web_access()(request)


def require_api_access(
    *,
    roles: Optional[Sequence[Role | str]] = None,
    permissions: Optional[Iterable[str]] = None,
):
    async def dependency(request: Request) -> dict:
        user = _get_session_user(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if not _is_authorized(user, roles, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )
        return user

    return dependency


async def require_api_user(request: Request) -> dict:
    return await require_api_access()(request)
