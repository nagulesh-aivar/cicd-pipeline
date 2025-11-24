from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """
    Application lifespan manager for OCR service.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting OCR Service...")
    logger.info("OCR Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OCR Service...")
    logger.info("OCR Service shutdown complete")
