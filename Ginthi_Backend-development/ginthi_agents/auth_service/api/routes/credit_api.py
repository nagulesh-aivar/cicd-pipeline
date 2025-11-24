from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.credit import CreditLedgerService
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/credit-ledger",
    tags=["AI Credits ledger"],
    responses={
        404: {"description": "Ledger not found"},
        500: {"description": "Internal server error"},
    },
)


def get_credit_ledger_service(
    db: AsyncSession = Depends(get_db)
) -> CreditLedgerService:
    """Dependency injection for CreditLedgerService"""
    return CreditLedgerService(db)


@router.get(
    "/{client_id}",
    response_model=StandardResponse,
    summary="Get client's credit ledger",
    description="Retrieve the credit ledger details for a specific client by ID. "
                "Use this endpoint to check available AI credits or transaction history."
)
async def get_ledger(
    client_id: int,
    service: CreditLedgerService = Depends(get_credit_ledger_service)
):
    """Fetch credit ledger details for a specific client"""
    return await service.get_ledger(client_id=client_id)


@router.post(
    "/{client_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update client credits",
    description="Add or deduct credits from a client’s ledger. "
                "Use this endpoint to modify available credits after a transaction or purchase."
)
async def add_to_ledger(
    client_id: int,
    change_amount: int,
    service: CreditLedgerService = Depends(get_credit_ledger_service)
):
    """Add or update credits for a specific client"""
    return await service.create_or_update_ledger(
        client_id=client_id,
        change_amount=change_amount
    )


@router.delete(
    "/{client_id}",
    response_model=StandardResponse,
    summary="Delete client ledger",
    description="Permanently delete a client’s credit ledger record. "
                "Use this endpoint only if the client is deactivated or removed."
)
async def delete_ledger(
    client_id: int,
    service: CreditLedgerService = Depends(get_credit_ledger_service)
):
    """Delete a client's credit ledger"""
    return await service.delete_ledger(client_id=client_id)
