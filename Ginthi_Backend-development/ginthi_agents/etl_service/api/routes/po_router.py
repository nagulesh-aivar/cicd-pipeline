from etl_service.api.schemas import ReportRequest, ReportResponse
from etl_service.services.auth_service import AuthService
from etl_service.services.browser_service import BrowserService
from etl_service.services.purchase_order_service import PurchaseOrderService
from etl_service.utils.logger import get_logger
from fastapi import APIRouter, BackgroundTasks, HTTPException

logger = get_logger(__name__)

router = APIRouter()


@router.post("/generate-po", response_model=ReportResponse)
async def generate_purchase_order_report(
    request: ReportRequest, background_tasks: BackgroundTasks
):
    """Generate Purchase Order Report from SupplyNote"""
    try:
        logger.info("Starting Purchase Order report generation request...")
        background_tasks.add_task(generate_po_report_task)

        return ReportResponse(
            status="processing",
            message="Purchase Order report generation started in background",
        )
    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_po_report_task():
    """Background task to generate Purchase Order report"""
    page = None
    try:
        logger.info("=== Starting Purchase Order Report Generation Task ===")

        # Get browser and create new page
        page = BrowserService.new_page()

        # Login
        login_success = AuthService.login(page)
        if not login_success:
            logger.error("Authentication failed")
            return

        # Navigate to Purchase Order report page
        nav_success = PurchaseOrderService.navigate_to_report(page)
        if not nav_success:
            logger.error("Navigation to Purchase Order report page failed")
            return

        # Set date range
        PurchaseOrderService.set_date_range(page)

        # Select filters (e.g., vendors/outlets)
        filter_success = PurchaseOrderService.select_all_filters(page)
        if not filter_success:
            logger.error("Filter selection failed")
            return

        # Generate report
        gen_success = PurchaseOrderService.generate_report(page)
        if not gen_success:
            logger.error("Report generation failed")
            return

        # Download report
        file_path = PurchaseOrderService.download_report(page)
        if not file_path:
            logger.error("Report download failed")
            return

        logger.info(f"=== Purchase Order Report Generation Completed Successfully ===")
        logger.info(f"Downloaded file path: {file_path}")

    except Exception as e:
        logger.error(f"Unexpected error in Purchase Order report generation: {str(e)}")
    finally:
        if page:
            page.close()
