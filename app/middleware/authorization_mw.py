import functools
from typing import Callable, Iterable

from fastapi import Depends, HTTPException, status
from fastapi import Request

from app.utils.acl import has_all_permissions, has_any_permission


def requires_permissions(*permissions: str) -> Callable:
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            user = request.state.user
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            if not has_all_permissions(user.permissions, permissions):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
            return await func(*args, request=request, **kwargs)

        return wrapper

    return decorator


def build_permission_dependency(required: Iterable[str]):
    async def dependency(request: Request = Depends()):
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        if not has_any_permission(user.permissions, required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return dependency
