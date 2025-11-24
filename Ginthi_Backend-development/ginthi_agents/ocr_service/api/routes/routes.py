from fastapi import APIRouter
from ocr_service.api.routes.openapi_router import router as openapi_router
from . import ocr_router

api_router = APIRouter()

# Include all routers
api_router.include_router(openapi_router, prefix="/api/v1", tags=["API Documentation"])
api_router.include_router(ocr_router.router, prefix="/api/v1", tags=["OCR"])
