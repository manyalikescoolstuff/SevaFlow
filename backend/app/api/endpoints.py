"""
API package — assembles all routers.
"""
from fastapi import APIRouter
from app.api.hardware import router as hardware_router
from app.api.customer import router as customer_router
from app.api.staff import router as staff_router
from app.api.workstation import router as workstation_router
from app.api.admin import router as admin_router

router = APIRouter()
router.include_router(hardware_router)
router.include_router(customer_router)
router.include_router(staff_router)
router.include_router(workstation_router)
router.include_router(admin_router)
