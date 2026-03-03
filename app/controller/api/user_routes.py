from fastapi import APIRouter, Depends

from app.service.user_service import UserService
from app.controller.schemas import ProfileResponse
from app.dependencies.auth import require_api_user
from app.dependencies.services import get_user_service

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
async def get_current_user_profile(_user: dict = Depends(require_api_user), service: UserService = Depends(get_user_service)):
    profile = await service.get_profile()
    return ProfileResponse.model_validate(profile)
