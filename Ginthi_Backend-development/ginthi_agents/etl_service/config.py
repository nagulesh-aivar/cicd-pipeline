import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # SupplyNote Configuration
    SUPPLYNOTE_BASE_URL: str = os.getenv("SUPPLYNOTE_BASE_URL", "https://supplynote.in")
    SUPPLYNOTE_USERNAME: str = os.getenv("SUPPLYNOTE_USERNAME", "ginthi.ai")
    SUPPLYNOTE_PASSWORD: str = os.getenv("SUPPLYNOTE_PASSWORD", "user@ABC123")
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DOWNLOADS_DIR = BASE_DIR / "downloads"
    LOGS_DIR = BASE_DIR / "logs"
    # Playwright settings
    BROWSER_HEADLESS: bool = False
    PAGE_TIMEOUT: int = 30000
    REPORT_WAIT_TIME: int = 600  # 10 minutes in seconds
    # API settings
    API_PORT: int = int(os.getenv("API_PORT", 8008))
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    EMAIL: str = "dev1@ginthi.ai"


settings = Settings()
settings.DOWNLOADS_DIR.mkdir(exist_ok=True)
settings.LOGS_DIR.mkdir(exist_ok=True)
