import time
from datetime import datetime
import pandas as pd

from etl_service.config import settings
from etl_service.utils.logger import get_logger
from playwright.sync_api import Page

logger = get_logger(__name__)


class VendorService:

    @staticmethod
    def navigate_to_my_suppliers(page: Page) -> bool:
        """Navigate to the My Suppliers page"""
        try:
            logger.info("Step 1: Clicking 'My Suppliers' button in sidebar...")

            # Wait for the My Suppliers button to be visible
            page.wait_for_selector('button:has-text("My Suppliers")', timeout=30000)

            # Click the My Suppliers button
            page.click('button:has-text("My Suppliers")', force=True)
            logger.info("'My Suppliers' button clicked")

            # Wait for page to load
            time.sleep(5)

            # Verify navigation was successful by checking for page elements
            logger.info("Verifying My Suppliers page loaded...")
            page.wait_for_selector('button[ng-click="vm.createCsv()"]', timeout=30000)
            logger.info("My Suppliers page loaded successfully")

            return True

        except Exception as e:
            logger.error(f"Navigation to My Suppliers failed: {e}")
            try:
                page.screenshot(path="my_suppliers_nav_error.png")
                logger.info("Error screenshot saved: my_suppliers_nav_error.png")
            except:
                pass
            return False

    @staticmethod
    def download_vendors_csv(page: Page) -> str:
        """Download the vendors CSV file from My Suppliers page"""
        try:
            logger.info("Looking for download button (file_download icon)...")

            # Wait for the download button to be visible
            download_button_selector = 'button[ng-click="vm.createCsv()"]'
            page.wait_for_selector(download_button_selector, timeout=30000)

            logger.info("Found download button, checking if it's enabled...")

            # Check if button is disabled
            is_disabled = page.get_attribute(download_button_selector, "aria-disabled")
            if is_disabled == "true":
                logger.error("Download button is disabled. CSV might still be loading.")
                return None

            logger.info("Initiating CSV download...")

            # Click the download button and wait for download
            with page.expect_download() as download_info:
                page.click(download_button_selector, force=True)
                logger.info("Download button clicked")

            download = download_info.value

            # Wait a moment for download to complete
            time.sleep(3)

            # Save the file with timestamp
            current_datetime = datetime.now()
            file_path = settings.DOWNLOADS_DIR / f"vendors_list_{current_datetime.strftime('%Y%m%d_%H%M%S')}.csv"
            download.save_as(str(file_path))

            logger.info(f"Vendors CSV downloaded successfully: {file_path}")

            df = pd.read_csv(file_path)
            df["data_version"] = current_datetime
            df.to_csv(file_path, index=False)
            logger.info("Added 'data_version' column to vendors CSV.")
            return str(file_path)

        except Exception as e:
            logger.error(f"Vendors CSV download failed: {e}")
            try:
                page.screenshot(path="vendors_download_error.png")
                logger.info("Error screenshot saved: vendors_download_error.png")
            except:
                pass
            return None
