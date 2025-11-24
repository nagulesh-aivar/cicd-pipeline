from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from ocr_service.api.constants.status_codes import StatusCode
import logging

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle all HTTPException errors and return uniform APIResponse format.
    """
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions and return uniform APIResponse format.
    """
    logger.error(
        f"Unhandled exception: {str(exc)} - Path: {request.url.path}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=StatusCode.INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "data": None
        }
    )


def register_exception_handlers(app):
    """
    Register all exception handlers to the FastAPI application.
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    logger.info("Exception handlers registered successfully")
