import time
from datetime import datetime
import pandas as pd

from etl_service.config import settings
from etl_service.utils.logger import get_logger
from playwright.sync_api import Page

logger = get_logger(__name__)


class PurchaseOrderService:

    @staticmethod
    def navigate_to_report(page: Page) -> bool:
        """Navigate to the Purchase Order Report page"""
        try:
            logger.info("Step 1: Clicking Reports button in sidebar...")
            page.wait_for_selector("text=Reports", timeout=30000)
            page.click("text=Reports", force=True)
            logger.info("Reports button clicked")
            time.sleep(3)

            logger.info("Step 2: Clicking 'PO-GRN Docs Report' card...")

            page.wait_for_selector("text=PO-GRN Docs Report", timeout=60000)
            page.click("text=PO-GRN Docs Report", force=True)
            logger.info("'PO-GRN Docs Report' card clicked")
            time.sleep(10)
            return True

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False

    @staticmethod
    def set_date_range(page: Page) -> bool:
        """Optionally modify the date range filter"""
        try:
            logger.info("Checking date range for Purchase Order Report...")
            time.sleep(1)
            logger.info("Date range kept as default.")
            return True

        except Exception as e:
            logger.error(f"Date range setup failed: {e}")
            return False

    @staticmethod
    def select_all_filters(page: Page) -> bool:
        """Select first few outlets/locations or vendors"""
        try:
            logger.info("Selecting filters for Purchase Order Report...")
            time.sleep(1)

            try:
                multiselect = page.query_selector(
                    'p-multiselect[formcontrolname="vendors"]'
                )
                if multiselect:
                    multiselect.click(force=True)
                    time.sleep(2)

                    checkboxes = page.query_selector_all(
                        'p-multiselect[formcontrolname="vendors"] .p-checkbox'
                    )
                    logger.info(f"Found {len(checkboxes)} vendor checkboxes")

                    count = 0
                    for checkbox in checkboxes:
                        if count >= 3:
                            break
                        checkbox.click(force=True)
                        count += 1
                        time.sleep(0.5)
                        logger.info(f"Selected vendor {count}")

                    page.click("body", force=True)
                    logger.info(f"{count} vendors selected.")
                else:
                    logger.warning("Vendor dropdown not found.")

            except Exception as e:
                logger.warning(f"Vendor selection failed: {e}")

            return True

        except Exception as e:
            logger.error(f"Filter selection failed: {e}")
            return False

    @staticmethod
    def generate_report(page: Page) -> bool:
        """Generate the Purchase Order report"""
        try:
            logger.info("Looking for 'Show Report' button...")
            page.wait_for_selector('button:has-text("Show Report")', timeout=15000)

            logger.info("Clicking 'Show Report' button...")
            page.click(
                'button.md-raised.md-primary.low-shadow-card:has-text("Show Report")',
                force=True,
            )

            logger.info("Waiting for report generation...")
            time.sleep(10)

            logger.info("Purchase Order report generated successfully.")
            return True

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return False

    @staticmethod
    def download_report(page: Page) -> str:
        """Download the latest generated Purchase Order report"""
        try:
            logger.info("Downloading Purchase Order report...")

            page.wait_for_selector('button:has-text("Export CSV")', timeout=30000)
            logger.info("Found 'Export CSV' button, initiating download...")

            export_button = page.query_selector('button:has-text("Export CSV")')

            if export_button:
                with page.expect_download() as download_info:
                    export_button.click(force=True)
                download = download_info.value

                current_datetime = datetime.now()
                file_path = (
                    settings.DOWNLOADS_DIR / f"purchase_order_report_{current_datetime.strftime('%Y%m%d_%H%M%S')}.csv"
                )
                download.save_as(str(file_path))

                df = pd.read_excel(file_path)
                df["data_version"] = current_datetime
                df.to_excel(file_path, index=False)
                logger.info("Added 'data_version' column to downloaded report.")

                logger.info(f"Report downloaded successfully: {file_path}")
                return str(file_path)
            else:
                logger.error("'Export CSV' button not found even after wait.")
                return None

        except Exception as e:
            logger.error(f"Report download failed: {e}")
            return None
