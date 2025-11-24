import time
from etl_service.config import settings
from etl_service.utils.logger import get_logger
from playwright.sync_api import Browser, Page, sync_playwright

logger = get_logger(__name__)


class BrowserService:
    _browser: Browser = None
    _playwright = None

    @classmethod
    def get_browser(cls) -> Browser:
        if cls._browser is None:
            logger.info("Launching Playwright browser...")
            cls._playwright = sync_playwright().start()
            cls._browser = cls._playwright.chromium.launch(
                headless=settings.BROWSER_HEADLESS
            )
        return cls._browser

    @classmethod
    def close_browser(cls):
        if cls._browser:
            logger.info("Closing browser...")
            cls._browser.close()
            cls._browser = None
        if cls._playwright:
            cls._playwright.stop()
            cls._playwright = None

    @classmethod
    def new_page(cls) -> Page:
        browser = cls.get_browser()
        page = browser.new_page()
        page.set_default_timeout(settings.PAGE_TIMEOUT)
        return page
