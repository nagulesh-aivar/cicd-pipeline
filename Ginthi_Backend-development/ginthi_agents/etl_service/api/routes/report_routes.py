from etl_service.api.schemas import ReportRequest, ReportResponse
from etl_service.services.auth_service import AuthService
from etl_service.services.browser_service import BrowserService
from etl_service.services.report_service import ReportService
from etl_service.utils.logger import get_logger
from fastapi import APIRouter, BackgroundTasks, HTTPException

logger = get_logger(__name__)

router = APIRouter()


@router.post("/generate-grn", response_model=ReportResponse)
async def generate_grn_report(
    request: ReportRequest, background_tasks: BackgroundTasks
):
    """Generate Item Wise GRN Report from SupplyNote"""
    try:
        logger.info("Starting GRN report generation request...")
        background_tasks.add_task(generate_report_task)

        return ReportResponse(
            status="processing", message="Report generation started in background"
        )
    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_report_task():
    """Background task to generate report"""
    page = None
    try:
        logger.info("=== Starting Report Generation Task ===")

        # Get browser and create new page
        page = BrowserService.new_page()

        # Login
        login_success = AuthService.login(page)
        if not login_success:
            logger.error("Authentication failed")
            return

        # Navigate to report page
        nav_success = ReportService.navigate_to_report(page)
        if not nav_success:
            logger.error("Navigation to report page failed")
            return

        # Set date range
        ReportService.set_date_range(page)

        # Select all filters
        filter_success = ReportService.select_all_filters(page)
        if not filter_success:
            logger.error("Filter selection failed")
            return

        # Generate report
        gen_success = ReportService.generate_report(page)
        if not gen_success:
            logger.error("Report generation failed")
            return

        # Download report
        file_path = ReportService.download_report(page)
        if not file_path:
            logger.error("Report download failed")
            return

        logger.info(f"=== Report Generation Completed Successfully ===")
        logger.info(f"File Path: {file_path}")

    except Exception as e:
        logger.error(f"Unexpected error in report generation: {str(e)}")
    finally:
        if page:
            page.close()


@router.post("/generate-grn-email", response_model=ReportResponse)
async def generate_grn_report_email(
    request: ReportRequest, background_tasks: BackgroundTasks
):
    """Generate Item Wise GRN Report and configure email via SupplyNote"""
    try:
        logger.info("Starting GRN report email generation request...")
        background_tasks.add_task(generate_report_email_task)

        return ReportResponse(
            status="processing",
            message="Report generation with email started in background",
        )
    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_report_email_task():
    """Background task to generate report with email configuration"""
    page = None
    try:
        logger.info("=== Starting Report Email Generation Task ===")

        # Get browser and create new page
        page = BrowserService.new_page()

        # Login
        login_success = AuthService.login(page)
        if not login_success:
            logger.error("Authentication failed")
            return

        # Navigate to report page
        nav_success = ReportService.navigate_to_report(page)
        if not nav_success:
            logger.error("Navigation to report page failed")
            return

        # Set date range
        ReportService.set_date_range(page)

        # Select all filters
        filter_success = ReportService.select_all_filters(page)
        if not filter_success:
            logger.error("Filter selection failed")
            return

        # Configure email
        email_success = ReportService.configure_email(page)
        if not email_success:
            logger.error("Email configuration failed")
            return

        # Generate report
        gen_success = ReportService.generate_report(page)
        if not gen_success:
            logger.error("Report generation failed")
            return

        logger.info("=== Report Email Generation Completed Successfully ===")
        logger.info("SupplyNote will send email automatically after 10 minutes")

    except Exception as e:
        logger.error(f"Unexpected error in report email generation: {str(e)}")
    finally:
        if page:
            page.close()


@router.post("/generate-report", response_model=ReportResponse)
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    """Generate Item Wise GRN Report (up to clicking Generate Report)"""
    try:
        logger.info("Starting GRN report generation request...")
        background_tasks.add_task(generate_report_only_task)

        return ReportResponse(
            status="processing", message="Report generation started in background"
        )
    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_report_only_task():
    """Background task to generate report up to clicking Generate Report"""
    page = None
    try:
        logger.info("=== Starting Report Generation Task (up to Generate) ===")

        # Get browser and create new page
        page = BrowserService.new_page()

        # Login
        login_success = AuthService.login(page)
        if not login_success:
            logger.error("Authentication failed")
            return

        # Navigate to report page (includes Item Wise GRN)
        nav_success = ReportService.navigate_to_report(page)
        if not nav_success:
            logger.error("Navigation to report page failed")
            return

        # Set date range
        date_success = ReportService.set_date_range(page)
        if not date_success:
            logger.error("Date range setting failed")
            return

        # Select all filters
        filter_success = ReportService.select_all_filters(page)
        if not filter_success:
            logger.error("Filter selection failed")
            return

        # Generate report
        gen_success = ReportService.generate_report(page)
        if not gen_success:
            logger.error("Report generation failed")
            return

        logger.info("=== Report Generation Completed Successfully (up to Generate) ===")

    except Exception as e:
        logger.error(f"Unexpected error in report generation: {str(e)}")
    finally:
        if page:
            page.close()


@router.post("/report-download", response_model=ReportResponse)
async def report_download(request: ReportRequest, background_tasks: BackgroundTasks):
    """Download Item Wise GRN Report file (includes generation if needed)"""
    try:
        logger.info("Starting GRN report download request...")
        background_tasks.add_task(download_report_task)

        return ReportResponse(
            status="processing", message="Report download started in background"
        )
    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def download_report_task():
    """Background task to download report (full process including generation)"""
    page = None
    try:
        logger.info("=== Starting Report Download Task ===")

        # Get browser and create new page
        page = BrowserService.new_page()

        # Login
        login_success = AuthService.login(page)
        if not login_success:
            logger.error("Authentication failed")
            return

        # Navigate to report page (includes Item Wise GRN)
        nav_success = ReportService.navigate_to_report(page)
        if not nav_success:
            logger.error("Navigation to report page failed")
            return

        # Download report
        file_path = ReportService.download_report(page)
        if not file_path:
            logger.error("Report download failed")
            return

        logger.info(f"=== Report Download Completed Successfully ===")
        logger.info(f"File Path: {file_path}")

    except Exception as e:
        logger.error(f"Unexpected error in report download: {str(e)}")
    finally:
        if page:
            page.close()
