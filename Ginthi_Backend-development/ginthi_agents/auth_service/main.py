# ginthi_agents/auth_service/main.py
import os

import uvicorn
import asyncio
from auth_service.api.routes.routers import api_router
from auth_service.utils.exception_handlers import register_exception_handlers
from auth_service.utils.lifespan import lifespan
from auth_service.utils.logging_config import setup_logging
from auth_service.utils.middlewares.middleware_manager import setup_middlewares
from auth_service.utils.security import security_dependency
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi_mcp import FastApiMCP

load_dotenv()

# Setup logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"), log_file=os.getenv("LOG_FILE", None)
)

# Initialize FastAPI app
# root_path allows FastAPI to work behind a reverse proxy with path prefix
app = FastAPI(
    title="Auth Serivce API",
    version="1.0.0",
    description="Auth Service API's",
    lifespan=lifespan,
    dependencies=[Depends(security_dependency)],
    root_path="/auth",  # Handle /auth prefix from ALB
)


# Register exception handlers
register_exception_handlers(app)

# Register all middlewares in one go
setup_middlewares(app)

# Include all API routes
app.include_router(api_router)


# 👇 THIS PART makes the "Authorize" button appear
def custom_openapi(request: Request = None):
    if app.openapi_schema and request is None:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    # Update servers URL - use API Gateway path if available, otherwise use root_path
    if request:
        # Check if accessed through API Gateway by examining the path
        path = str(request.url.path)
        # If accessed through API Gateway (/api/v1/auth), use that path
        if '/api/v1/auth' in path:
            # Extract the base path (everything before /openapi.json or /docs)
            base_path = '/api/v1/auth'
            openapi_schema["servers"] = [{"url": base_path}]
        elif app.root_path:
            openapi_schema["servers"] = [{"url": app.root_path}]
    elif app.root_path:
        openapi_schema["servers"] = [{"url": app.root_path}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # ✅ attach our schema override

# Override /openapi.json endpoint to pass request for dynamic server URL
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint(request: Request):
    return custom_openapi(request)

# Override /docs endpoint to inject correct OpenAPI JSON path
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    # Determine the correct path for openapi.json based on request
    path = str(request.url.path)
    if '/api/v1/auth' in path:
        openapi_url = '/api/v1/auth/openapi.json'
    else:
        openapi_url = f"{app.root_path}/openapi.json" if app.root_path else "/openapi.json"
    
    # Get the base URL for oauth redirect
    base_url = str(request.base_url).rstrip('/')
    oauth_redirect_url = f"{base_url}{openapi_url.replace('/openapi.json', '/docs/oauth2-redirect')}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
        <title>{app.title} - Swagger UI</title>
    </head>
    <body>
        <div id="swagger-ui">
        </div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
        const ui = SwaggerUIBundle({{
            url: '{openapi_url}',
            dom_id: "#swagger-ui",
            layout: "BaseLayout",
            deepLinking: true,
            showExtensions: true,
            showCommonExtensions: true,
            oauth2RedirectUrl: '{oauth_redirect_url}',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
        }})
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/health-check", tags=["Health Check"])
async def health_check():
    return {
        "success": True,
        "message": "Service is healthy",
        "data": {"status": "healthy", "service": "Auth Service API"},
    }

def main():
    """
    Main function to run the application with uvicorn.
    """
    uvicorn.run(
        "auth_service.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        workers=int(os.getenv("WORKERS", 4)),
    )


if __name__ == "__main__":
    main()
