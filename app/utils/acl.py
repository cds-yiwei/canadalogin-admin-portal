from typing import Iterable, Set


def has_permission(user_permissions: Iterable[str], required: str) -> bool:
    return required in set(user_permissions)


def has_any_permission(user_permissions: Iterable[str], required: Iterable[str]) -> bool:
    user_set: Set[str] = set(user_permissions)
    return any(perm in user_set for perm in required)


def has_all_permissions(user_permissions: Iterable[str], required: Iterable[str]) -> bool:
    user_set: Set[str] = set(user_permissions)
    return all(perm in user_set for perm in required)
