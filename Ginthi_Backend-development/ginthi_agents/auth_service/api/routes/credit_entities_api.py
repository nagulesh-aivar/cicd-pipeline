from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.credit_entities import CreditEntryService
from auth_service.schemas.pydantic_schema.credit_schemas import CreditEntryCreate, CreditEntryUpdate
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/credit-entities",
    tags=["AI Credit Entities"],
    responses={
        404: {"description": "Credit entry not found"},
        500: {"description": "Internal server error"},
    },
)


def get_credit_entry_service(
    db: AsyncSession = Depends(get_db)
) -> CreditEntryService:
    """Dependency injection for CreditEntryService"""
    return CreditEntryService(db)


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a credit entry",
    description="Create a new credit entry for a client. "
                "Use this endpoint to log credit transactions such as top-ups or deductions."
)
async def create_entry(
    entry: CreditEntryCreate,
    service: CreditEntryService = Depends(get_credit_entry_service)
):
    """Create a new credit entry"""
    return await service.create_credit_entry(**entry.dict())


@router.get(
    "/",
    response_model=StandardResponse,
    summary="List all credit entries",
    description="Retrieve a paginated list of all credit entries. "
                "Use this endpoint to view credit transactions across all clients."
)
async def list_entries(
    skip: int = 0,
    limit: int = 100,
    service: CreditEntryService = Depends(get_credit_entry_service)
):
    """List all credit entries with pagination"""
    return await service.get_credit_entries(skip=skip, limit=limit)


@router.get(
    "/{entry_id}",
    response_model=StandardResponse,
    summary="Get a credit entry by ID",
    description="Retrieve details of a specific credit entry using its ID. "
                "Use this endpoint to view details of a particular credit transaction."
)
async def get_entry(
    entry_id: int,
    service: CreditEntryService = Depends(get_credit_entry_service)
):
    """Get details of a specific credit entry"""
    return await service.get_credit_entry(entry_id=entry_id)


@router.put(
    "/{entry_id}",
    response_model=StandardResponse,
    summary="Update a credit entry",
    description="Update fields of an existing credit entry such as amount or description. "
                "Use this endpoint for correcting or modifying entry details."
)
async def update_entry(
    entry_id: int,
    entry_update: CreditEntryUpdate,
    service: CreditEntryService = Depends(get_credit_entry_service)
):
    """Update a credit entry"""
    return await service.update_credit_entry(
        entry_id=entry_id,
        data=entry_update.dict(exclude_unset=True)
    )


@router.delete(
    "/{entry_id}",
    response_model=StandardResponse,
    summary="Delete a credit entry",
    description="Permanently delete a credit entry from the system. "
                "Use this endpoint with caution as it removes historical transaction data."
)
async def delete_entry(
    entry_id: int,
    service: CreditEntryService = Depends(get_credit_entry_service)
):
    """Delete a credit entry"""
    return await service.delete_credit_entry(entry_id=entry_id)
