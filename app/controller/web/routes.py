from fastapi import APIRouter

# Aggregated web router that composes smaller route modules for separation of concerns
from .auth_routes import router as auth_router
from .applications_routes import router as applications_router
from .group_management_routes import router as group_management_router

# Create root router and include subrouters
router = APIRouter()
router.include_router(auth_router)
router.include_router(applications_router)
router.include_router(group_management_router)
# fragments are mounted separately in app.main; keep the module for compatibility
