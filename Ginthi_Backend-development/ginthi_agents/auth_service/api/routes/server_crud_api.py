from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.server_crud import ClientServerService
from auth_service.schemas.pydantic_schema.server_schemas import ClientServerCreate, ClientServerUpdate
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/client-servers",
    tags=["Client Servers"],
    responses={
        404: {"description": "Server not found"},
        500: {"description": "Internal server error"},
    },
)


def get_client_server_service(db: AsyncSession = Depends(get_db)) -> ClientServerService:
    """Dependency injection for ClientServerService"""
    return ClientServerService(db)


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a client server",
    description="Register a new client server. Use this endpoint when adding a server for a client."
)
async def create_server(
    server: ClientServerCreate,
    service: ClientServerService = Depends(get_client_server_service)
):
    """Create a new client server"""
    return await service.create_server(**server.dict())


@router.get(
    "/{server_id}",
    response_model=StandardResponse,
    summary="Retrieve a client server by ID",
    description="Fetch details of a client server using its unique ID."
)
async def get_server(
    server_id: int,
    service: ClientServerService = Depends(get_client_server_service)
):
    """Get a client server by ID"""
    return await service.get_server(server_id)


@router.put(
    "/{server_id}",
    response_model=StandardResponse,
    summary="Update a client server",
    description="Modify details of an existing client server. Use this endpoint to update server info."
)
async def update_server(
    server_id: int,
    server: ClientServerUpdate,
    service: ClientServerService = Depends(get_client_server_service)
):
    """Update an existing client server"""
    return await service.update_server(server_id, **server.dict(exclude_unset=True))


@router.delete(
    "/{server_id}",
    response_model=StandardResponse,
    summary="Delete a client server",
    description="Permanently remove a client server by its unique ID."
)
async def delete_server(
    server_id: int,
    service: ClientServerService = Depends(get_client_server_service)
):
    """Delete a client server by ID"""
    return await service.delete_server(server_id)
