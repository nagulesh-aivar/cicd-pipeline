from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.client_api_keys import ClientAPIKeyService
from auth_service.schemas.pydantic_schema.client_schemas import ClientAPIKeyCreate, ClientAPIKeyUpdate
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/client-api-keys",
    tags=["Client API Keys"],
    responses={
        404: {"description": "API Key not found"},
        500: {"description": "Internal server error"},
    },
)


def get_client_api_key_service(
    db: AsyncSession = Depends(get_db)
) -> ClientAPIKeyService:
    """Dependency injection for ClientAPIKeyService"""
    return ClientAPIKeyService(db)


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API Key",
    description="Generate a new API key for a client. Use this endpoint when registering a new client or regenerating keys."
)
async def create_api_key(
    api_key: ClientAPIKeyCreate,
    service: ClientAPIKeyService = Depends(get_client_api_key_service)
):
    """Create a new client API key"""
    return await service.create_api_key(**api_key.dict())


@router.get(
    "/",
    response_model=StandardResponse,
    summary="List all client API keys",
    description="Retrieve a paginated list of all client API keys. Use this to manage and monitor existing client API credentials."
)
async def list_api_keys(
    skip: int = 0,
    limit: int = 100,
    service: ClientAPIKeyService = Depends(get_client_api_key_service)
):
    """List all API keys"""
    return await service.get_api_keys(skip=skip, limit=limit)


@router.get(
    "/{api_key_id}",
    response_model=StandardResponse,
    summary="Get API key by ID",
    description="Retrieve details of a specific client API key by its unique ID."
)
async def get_api_key(
    api_key_id: int,
    service: ClientAPIKeyService = Depends(get_client_api_key_service)
):
    """Get details of a specific API key"""
    return await service.get_api_key(api_key_id=api_key_id)


@router.put(
    "/{api_key_id}",
    response_model=StandardResponse,
    summary="Update an existing API key",
    description="Modify the details of an existing client API key such as status or metadata."
)
async def update_api_key(
    api_key_id: int,
    api_key_update: ClientAPIKeyUpdate,
    service: ClientAPIKeyService = Depends(get_client_api_key_service)
):
    """Update an existing API key"""
    return await service.update_api_key(
        api_key_id=api_key_id,
        data=api_key_update.dict(exclude_unset=True)
    )


@router.delete(
    "/{api_key_id}",
    response_model=StandardResponse,
    summary="Delete a client API key",
    description="Permanently delete a client API key by ID. Use this when revoking access for a client."
)
async def delete_api_key(
    api_key_id: int,
    service: ClientAPIKeyService = Depends(get_client_api_key_service)
):
    """Delete a client API key"""
    return await service.delete_api_key(api_key_id=api_key_id)
