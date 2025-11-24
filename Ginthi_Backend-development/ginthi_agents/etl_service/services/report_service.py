import time
from datetime import datetime
import pandas as pd

from etl_service.config import settings
from etl_service.utils.logger import get_logger
from playwright.sync_api import Page

logger = get_logger(__name__)


class ReportService:

    @staticmethod
    def navigate_to_report(page: Page) -> bool:
        try:
            logger.info("Step 1: Clicking Reports button in sidebar...")
            page.click('button:has-text("Reports")', force=True)
            logger.info("Reports button clicked")
            time.sleep(3)

            logger.info("Step 2: Clicking Item Wise GRN Report V2 card...")
            page.click('[ui-sref="reports.itemWiseGRN"]', force=True)
            logger.info("Item Wise GRN card clicked")
            time.sleep(10)

            return True

        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            return False

    @staticmethod
    def set_date_range(page: Page) -> bool:
        try:
            logger.info("Checking date range...")
            logger.info("Date range using defaults - not modified")
            return True
        except Exception as e:
            logger.error(f"Date range check failed: {str(e)}")
            return False

    @staticmethod
    def select_all_filters(page: Page) -> bool:
        try:
            logger.info("Starting filter selection...")
            time.sleep(1)

            iframe_element = page.wait_for_selector("iframe.ng-isolate-scope")
            frame = iframe_element.content_frame()

            logger.info(
                "Looking for Location dropdown (p-multiselect) inside iframe..."
            )

            try:
                frame.wait_for_selector(
                    'p-multiselect[formcontrolname="outlets"]', timeout=10000
                )

                multiselect_button = frame.locator(
                    'p-multiselect[formcontrolname="outlets"]'
                )

                multiselect_button.click(force=True)
                logger.info("Location dropdown opened")
                time.sleep(2)

                logger.info("Looking for Select All checkbox...")
                select_all_checkbox = frame.locator(
                    'div[role="checkbox"].p-checkbox-box'
                ).first

                select_all_checkbox.wait_for(state="visible", timeout=10000)
                select_all_checkbox.scroll_into_view_if_needed()
                time.sleep(1)

                select_all_checkbox.click(force=True)
                logger.info("Clicked Select All checkbox - all locations selected!")

                time.sleep(2)

                frame.click("body", force=True)
                time.sleep(1)

                logger.info(
                    "Filter selection completed - all locations selected at once"
                )
                return True

            except Exception as e:
                logger.warning(f"Location selection error: {str(e)}")
                return True

        except Exception as e:
            logger.error(f"Filter selection failed: {str(e)}")
            return False

    @staticmethod
    def configure_email(page: Page) -> bool:
        try:
            logger.info("Configuring email settings...")
            time.sleep(1)

            iframe_element = page.wait_for_selector("iframe.ng-isolate-scope")
            frame = iframe_element.content_frame()

            logger.info("Enabling 'Send Report on Email' checkbox by clicking box...")
            checkbox_box = frame.locator("div.p-checkbox-box").first
            checkbox_box.wait_for(state="visible", timeout=10000)
            checkbox_box.click(force=True)
            logger.info("Checkbox enabled via box click")
            time.sleep(1)

            checkbox_input = frame.locator("input#sendMail")
            aria_checked = checkbox_input.get_attribute("aria-checked")
            if aria_checked != "true":
                logger.warning("Checkbox not checked after click; retrying...")
                checkbox_box.click(force=True)
                time.sleep(1)
                aria_checked = checkbox_input.get_attribute("aria-checked")
                if aria_checked != "true":
                    raise Exception("Failed to enable checkbox after retry")
            logger.info("Checkbox confirmed enabled")
            time.sleep(1)

            logger.info("Removing default email...")
            remove_icon = frame.locator("timescircleicon").first
            remove_icon.wait_for(state="visible", timeout=5000)
            remove_icon.click(force=True)
            logger.info("Default email removed")
            time.sleep(1)

            logger.info("Typing new email...")
            email_input = frame.locator('input[placeholder="Enter e-mail ids"]')
            email_input.wait_for(state="visible", timeout=10000)
            email_input.clear()
            email_input.fill(settings.EMAIL)
            time.sleep(1)

            logger.info("Clicking Add button...")
            add_button = frame.locator('span.p-button-label:has-text("Add")')
            add_button.wait_for(state="visible", timeout=5000)
            add_button.click(force=True)
            logger.info("Email added via Add button")
            time.sleep(2)

            logger.info("Email configuration completed")
            return True

        except Exception as e:
            logger.error(f"Email configuration failed: {str(e)}")
            return False

    @staticmethod
    def generate_report(page: Page) -> bool:
        try:
            logger.info("Looking for Generate Report button...")
            time.sleep(1)

            logger.info("Clicking 'Generate Report' button...")

            iframe_element = page.wait_for_selector("iframe.ng-isolate-scope")
            frame = iframe_element.content_frame()

            frame.wait_for_selector("span.p-button-label", timeout=180000)

            button = frame.locator("span.p-button-label", has_text="Generate Report")

            button.wait_for(state="visible", timeout=10000)
            button.click()
            print("Clicked 'Generate Report' button successfully!")

            logger.info("Waiting 1 minutes for report generation...")
            time.sleep(60)

            logger.info("Report generation completed")
            return True
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            return False

    @staticmethod
    def download_report(page: Page, reference_id: str = None) -> str:
        try:
            logger.info("Downloading latest report...")

            iframe_element = page.wait_for_selector("iframe.ng-isolate-scope")
            frame = iframe_element.content_frame()

            frame.wait_for_selector("tbody.p-datatable-tbody", timeout=10000)
            time.sleep(2)

            first_row = frame.locator("tbody.p-datatable-tbody tr").first
            first_row.wait_for(state="visible", timeout=10000)

            download_button = first_row.locator(
                "span.p-button-label", has_text="Download"
            )
            download_button.wait_for(state="visible", timeout=10000)

            logger.info("Clicking Download button for latest report...")
            with page.expect_download() as download_info:
                download_button.click(force=True)

            download = download_info.value
            time.sleep(10)

            current_datetime = datetime.now()
            file_path = settings.DOWNLOADS_DIR / f"item_wise_grn_report_{current_datetime.strftime('%Y%m%d_%H%M%S')}.csv"
            download.save_as(str(file_path))

            logger.info(f"Report downloaded: {file_path}")

            df = pd.read_csv(file_path)

            df["data_version"] = current_datetime  # or int(1)

            # Save back the updated file
            df.to_csv(file_path, index=False)
            logger.info("Added 'data_version' column to downloaded report.")
            return str(file_path)

        except Exception as e:
            logger.error(f"Report download failed: {str(e)}")
            return None
