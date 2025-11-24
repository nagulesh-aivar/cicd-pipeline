from contextlib import contextmanager

import uvicorn
from etl_service.api.routes.routers import api_router
from etl_service.config import settings
from etl_service.services.browser_service import BrowserService
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import atexit


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(
        title="SupplyNote GRN Report Automation",
        description="Automated ETL service for SupplyNote GRN reports",
        version="1.0.0",
    )

    # Register cleanup on shutdown
    atexit.register(BrowserService.close_browser)

    # CORS setup
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "ETL service is running"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "etl_service.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info",
        reload=True,
    )
