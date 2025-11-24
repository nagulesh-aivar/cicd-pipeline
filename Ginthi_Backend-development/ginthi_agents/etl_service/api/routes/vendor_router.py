from etl_service.api.schemas import ReportRequest, ReportResponse
from etl_service.services.auth_service import AuthService
from etl_service.services.browser_service import BrowserService
from etl_service.services.vendor_service import VendorService
from etl_service.utils.logger import get_logger
from fastapi import APIRouter, BackgroundTasks, HTTPException

logger = get_logger(__name__)

router = APIRouter()


@router.post("/download-vendors-csv", response_model=ReportResponse)
async def download_vendors_csv(
    request: ReportRequest, background_tasks: BackgroundTasks
):
    """Download vendors CSV directly (alternate endpoint)"""
    try:
        logger.info("Starting vendor CSV download request...")
        background_tasks.add_task(download_vendors_csv_task)

        return ReportResponse(
            status="processing",
            message="Vendor CSV download started in background",
        )
    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def download_vendors_csv_task():
    """Background task to download vendors CSV"""
    page = None
    try:
        logger.info("=== Starting Vendor CSV Download Task ===")

        # Get browser and create new page
        page = BrowserService.new_page()

        # Login
        login_success = AuthService.login(page)
        if not login_success:
            logger.error("Authentication failed")
            return

        # Navigate to My Suppliers page
        nav_success = VendorService.navigate_to_my_suppliers(page)
        if not nav_success:
            logger.error("Navigation to My Suppliers failed")
            return

        # Download CSV
        file_path = VendorService.download_vendors_csv(page)
        if not file_path:
            logger.error("Vendor CSV download failed")
            return

        logger.info(f"=== Vendor CSV Download Completed Successfully ===")
        logger.info(f"Downloaded file path: {file_path}")

    except Exception as e:
        logger.error(f"Unexpected error in vendor CSV download: {str(e)}")
    finally:
        if page:
            page.close()
