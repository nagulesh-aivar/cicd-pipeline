from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.credit_models import AICreditLedger
from auth_service.schemas.pydantic_schema.credit_schemas import CreditLedgerOut
from fastapi import HTTPException
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import CreditLedgerMessages
from auth_service.utils.response_schema import StandardResponse
import logging

logger = logging.getLogger(__name__)

class CreditLedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_ledger(self, client_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(AICreditLedger).where(AICreditLedger.client_id == client_id)
            )
            ledger = result.scalar_one_or_none()
            if not ledger:
                logger.error(CreditLedgerMessages.NOT_FOUND.format(client_id=client_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=CreditLedgerMessages.NOT_FOUND.format(client_id=client_id)
                )
            logger.info(CreditLedgerMessages.RETRIEVED_SUCCESS.format(client_id=client_id))
            ledger_out = [CreditLedgerOut.model_validate(ledger)]
            return StandardResponse(
                status=True,
                message=CreditLedgerMessages.RETRIEVED_SUCCESS.format(client_id=client_id),
                data=ledger_out
            )
        except Exception as e:
            logger.exception(CreditLedgerMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=CreditLedgerMessages.INTERNAL_SERVER_ERROR
            )

    async def create_or_update_ledger(self, client_id: int, change_amount: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(AICreditLedger).where(AICreditLedger.client_id == client_id)
            )
            ledger = result.scalar_one_or_none()
            if ledger:
                ledger.current_balance += change_amount
                logger.info(f"Updating ledger for client_id={client_id} by {change_amount}")
            else:
                ledger = AICreditLedger(client_id=client_id, current_balance=change_amount)
                self.db.add(ledger)
                logger.info(f"Creating new ledger for client_id={client_id} with balance {change_amount}")
            await self.db.commit()
            await self.db.refresh(ledger)
            ledger_out = [CreditLedgerOut.model_validate(ledger)]
            return StandardResponse(
                status=True,
                message=CreditLedgerMessages.UPDATED_SUCCESS.format(client_id=client_id),
                data=ledger_out
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(CreditLedgerMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=CreditLedgerMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_ledger(self, client_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(AICreditLedger).where(AICreditLedger.client_id == client_id)
            )
            ledger = result.scalar_one_or_none()
            if not ledger:
                logger.error(CreditLedgerMessages.NOT_FOUND.format(client_id=client_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=CreditLedgerMessages.NOT_FOUND.format(client_id=client_id)
                )
            await self.db.delete(ledger)
            await self.db.commit()
            logger.info(CreditLedgerMessages.DELETED_SUCCESS.format(client_id=client_id))
            return StandardResponse(
                status=True,
                message=CreditLedgerMessages.DELETED_SUCCESS.format(client_id=client_id)
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(CreditLedgerMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=CreditLedgerMessages.INTERNAL_SERVER_ERROR
            )
