from etl_service.api.routes import po_router, report_routes, vendor_router, transform_routes
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(
    report_routes.router, prefix="/api/v1/supply_note/reports", tags=["GRN Reports"]
)
api_router.include_router(
    po_router.router,
    prefix="/api/v1/supply_note/reports",
    tags=["Purchase Order Reports"],
)

api_router.include_router(
    vendor_router.router,
    prefix="/api/v1/supply_note/vendors",
    tags=["Vendor Management"],
)

api_router.include_router(
    transform_routes.router,
    prefix="/api/v1/transform",
    tags=["Data Transformation"],
)

