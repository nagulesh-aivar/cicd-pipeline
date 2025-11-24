from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from auth_service.db.postgres_db import init_db, close_db
from auth_service.utils.middlewares.transaction_middleware import upload_logs_to_s3
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan: startup and shutdown events.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting application...")
    try:
        await init_db()
        logger.info("PostgreSQL Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    stop_event = asyncio.Event()

    async def periodic_upload():
        """Upload logs to S3 periodically."""
        while not stop_event.is_set():
            try:
                await upload_logs_to_s3()
            except Exception as e:
                logger.error(f"Error in log upload task: {e}", exc_info=True)
            await asyncio.sleep(3600)  # every 1 hour

    task = asyncio.create_task(periodic_upload())
    logger.info(" Background S3 log uploader started.")

    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    stop_event.set()
    task.cancel()
    try:
        await close_db()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")