from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.lead_admins import LeadAdminService
from auth_service.schemas.pydantic_schema.client_schemas import LeadAdminCreate, LeadAdminUpdate
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/lead-admins",
    tags=["Lead Admins"],
    responses={
        404: {"description": "Lead Admin not found"},
        500: {"description": "Internal server error"},
    },
)


def get_lead_admin_service(db: AsyncSession = Depends(get_db)) -> LeadAdminService:
    """Dependency injection for LeadAdminService"""
    return LeadAdminService(db)


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lead admin",
    description="Register a new lead admin for a client organization. "
                "Use this endpoint when onboarding a new lead admin."
)
async def create_lead_admin(
    lead_admin: LeadAdminCreate,
    service: LeadAdminService = Depends(get_lead_admin_service)
):
    """Create a new lead admin"""
    return await service.create_lead_admin(**lead_admin.dict())


@router.get(
    "/",
    response_model=StandardResponse,
    summary="List all lead admins",
    description="Retrieve a paginated list of all registered lead admins. "
                "Use this endpoint to view all admins assigned to clients."
)
async def list_lead_admins(
    skip: int = 0,
    limit: int = 100,
    service: LeadAdminService = Depends(get_lead_admin_service)
):
    """List all lead admins with pagination"""
    return await service.get_lead_admins(skip=skip, limit=limit)


@router.get(
    "/{lead_admin_id}",
    response_model=StandardResponse,
    summary="Retrieve a lead admin by ID",
    description="Fetch a specific lead admin’s details using their unique ID. "
                "Use this endpoint to get detailed admin profile information."
)
async def get_lead_admin_by_id(
    lead_admin_id: int,
    service: LeadAdminService = Depends(get_lead_admin_service)
):
    """Retrieve a single lead admin by ID"""
    return await service.get_lead_admin_by_id(lead_admin_id=lead_admin_id)


@router.put(
    "/{lead_admin_id}",
    response_model=StandardResponse,
    summary="Update a lead admin",
    description="Modify an existing lead admin’s details such as name, email, or phone. "
                "Use this endpoint to update admin profile information."
)
async def update_lead_admin(
    lead_admin_id: int,
    lead_admin: LeadAdminUpdate,
    service: LeadAdminService = Depends(get_lead_admin_service)
):
    """Update an existing lead admin"""
    return await service.update_lead_admin(
        lead_admin_id=lead_admin_id,
        data=lead_admin.dict(exclude_unset=True)
    )


@router.delete(
    "/{lead_admin_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a lead admin",
    description="Permanently remove a lead admin from the system using their unique ID. "
                "Use this endpoint to revoke access for an inactive admin."
)
async def delete_lead_admin(
    lead_admin_id: int,
    service: LeadAdminService = Depends(get_lead_admin_service)
):
    """Delete a lead admin by ID"""
    return await service.delete_lead_admin(lead_admin_id=lead_admin_id)
