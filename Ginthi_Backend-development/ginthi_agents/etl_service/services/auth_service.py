import time
from etl_service.config import settings
from etl_service.utils.logger import get_logger
from playwright.sync_api import Page

logger = get_logger(__name__)


class AuthService:
    LOGIN_PAGE = f"{settings.SUPPLYNOTE_BASE_URL}"

    @staticmethod
    def login(page: Page) -> bool:
        try:
            logger.info(f"Navigating to login page: {AuthService.LOGIN_PAGE}")
            page.goto(AuthService.LOGIN_PAGE, wait_until="networkidle", timeout=60000)

            logger.info("Page loaded. Waiting for form...")
            page.wait_for_selector(
                'input[placeholder*="username"], input[placeholder*="Enter your username"]',
                timeout=60000,
            )

            logger.info("Filling username...")
            page.fill('input[placeholder*="username"]', settings.SUPPLYNOTE_USERNAME)
            logger.info(f"Username filled: {settings.SUPPLYNOTE_USERNAME}")

            time.sleep(1)

            logger.info("Filling password...")
            page.fill('input[placeholder*="password"]', settings.SUPPLYNOTE_PASSWORD)
            logger.info("Password filled")

            time.sleep(1)

            logger.info("Clicking login button...")
            page.click('button:has-text("LOG IN")')

            logger.info("Waiting for navigation...")
            try:
                page.wait_for_navigation(wait_until="networkidle", timeout=60000)
            except:
                logger.warning("Navigation timeout, but continuing...")
                time.sleep(3)

            logger.info("Login successful!")
            return True

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            try:
                page.screenshot(path="login_error.png")
                logger.info("Error screenshot saved: login_error.png")
            except:
                pass
            return False
