from fastapi import APIRouter
from auth_service.api.routes import (openapi_router, client_api_keys_api, clients_api, credit_api, credit_entities_api,
                                     feedback_api, lead_admins_api, server_crud_api, workflow_api,
                                     workflow_execution_api)

from .openapi_router import router as openapi_router

api_router = APIRouter()

api_router.include_router(openapi_router, prefix="/api/v1", tags=["API Documentation"])
api_router.include_router(clients_api.router, prefix="/api/v1/clients", tags=["Clients"])
api_router.include_router(lead_admins_api.router, prefix="/api/v1/lead_admins", tags=["Lead Admins"])
api_router.include_router(client_api_keys_api.router, prefix="/api/v1/api_keys", tags=["Client API Keys"])
api_router.include_router(server_crud_api.router, prefix="/api/v1/servers", tags=["Client Servers"])
api_router.include_router(workflow_api.router, prefix="/api/v1/workflows", tags=["Workflows"])
api_router.include_router(workflow_execution_api.router, prefix="/api/v1/workflowexecution", tags=["Workflow Executions"])
api_router.include_router(credit_api.router, prefix="/api/v1/credits", tags=["AI Credits ledger"])
api_router.include_router(credit_entities_api.router, prefix="/api/v1/credits_entities", tags=["AI Credit Entities"])
api_router.include_router(feedback_api.router, prefix="/api/v1/feedback", tags=["Feedback"])
