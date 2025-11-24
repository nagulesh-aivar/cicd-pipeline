from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.clients import ClientService
from auth_service.schemas.pydantic_schema.client_schemas import ClientCreate, ClientUpdate
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/clients",
    tags=["Clients"],
    responses={
        404: {"description": "Client not found"},
        500: {"description": "Internal server error"}
    },
)


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a client",
    description="Create a new client in the system. Use this endpoint when adding a new client."
)
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new client"""
    service = ClientService(db)
    return await service.create_client(**client_data.dict())


@router.get(
    "/{client_id}",
    response_model=StandardResponse,
    summary="Get client by ID",
    description="Retrieve client details by ID. Use this to view information for a specific client."
)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a client by ID"""
    service = ClientService(db)
    return await service.get_client(client_id)


@router.get(
    "/",
    response_model=StandardResponse,
    summary="List all clients",
    description="Retrieve a paginated list of all clients. Use this to list all clients with optional pagination."
)
async def list_clients(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all clients with pagination"""
    service = ClientService(db)
    return await service.get_clients(skip=skip, limit=limit)


@router.put(
    "/{client_id}",
    response_model=StandardResponse,
    summary="Update a client",
    description="Update client details such as name or email. Use this endpoint to modify client information."
)
async def update_client(
    client_id: int,
    client_data: ClientUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update client details"""
    service = ClientService(db)
    return await service.update_client(client_id, client_data.dict(exclude_unset=True))


@router.delete(
    "/{client_id}",
    response_model=StandardResponse,
    summary="Delete a client",
    description="Permanently delete a client by ID. Use this endpoint to remove a client from the system."
)
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a client"""
    service = ClientService(db)
    return await service.delete_client(client_id)
