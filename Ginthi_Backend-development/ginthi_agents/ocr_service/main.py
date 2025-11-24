from fastapi import FastAPI
from ocr_service.api.routes.routes import api_router
from ocr_service.utils import register_exception_handlers, setup_logging
from ocr_service.utils.lifespan import lifespan
import uvicorn
import os

from dotenv import load_dotenv

load_dotenv()

# Setup logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", None)
)

# Create FastAPI application
app = FastAPI(
    title="OCR Service API",
    version="1.0.0",
    description="Advanced OCR Service API for document text extraction",
    lifespan=lifespan
)

# Register exception handlers
register_exception_handlers(app)

# Include all API routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "success": True,
        "message": "OCR Service API is running",
        "data": {
            "version": "1.0.0",
            "service": "OCR Document Processing",
            "supported_formats": ["PDF", "PNG", "JPEG", "JPG", "TIFF", "BMP"]
        }
    }


@app.get("/health")
async def health_check():
    return {
        "success": True,
        "message": "Service is healthy",
        "data": {
            "status": "healthy",
            "service": "OCR Document Processing"
        }
    }


def main():
    """
    Main function to run the application with uvicorn.
    """
    uvicorn.run(
        "ocr_service.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8006)),
        reload=os.getenv("RELOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),    
        workers=int(os.getenv("WORKERS", 1))
    )


if __name__ == "__main__":
    main()