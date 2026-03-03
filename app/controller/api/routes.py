from fastapi import APIRouter

# Aggregated API router that composes smaller routers
from .admin_routes import router as admin_router
from .user_routes import router as user_router

router = APIRouter(prefix="/api/v1")
# include admin and user routers (they already use the /api/v1 prefix)
router.include_router(admin_router)
router.include_router(user_router)
