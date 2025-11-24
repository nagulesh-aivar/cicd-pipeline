from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.credit_models import AICreditEntries
from auth_service.schemas.pydantic_schema.credit_schemas import CreditEntryOut
from fastapi import HTTPException
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import CreditEntryMessages
from auth_service.utils.response_schema import StandardResponse
import logging

logger = logging.getLogger(__name__)

class CreditEntryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_credit_entry(self, **kwargs) -> StandardResponse:
        try:
            entry = AICreditEntries(**kwargs)
            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)
            logger.info(CreditEntryMessages.CREATED_SUCCESS.format(id=entry.credit_entry_id))
            entry_out = [CreditEntryOut.model_validate(entry)]
            return StandardResponse(
                status=True,
                message=CreditEntryMessages.CREATED_SUCCESS.format(id=entry.credit_entry_id),
                data=entry_out
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(CreditEntryMessages.CREATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=CreditEntryMessages.INTERNAL_SERVER_ERROR
            )

    async def get_credit_entries(self, skip: int = 0, limit: int = 100) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(AICreditEntries).offset(skip).limit(limit)
            )
            entries = result.scalars().all()
            logger.info(CreditEntryMessages.RETRIEVED_ALL_SUCCESS.format(count=len(entries)))
            entries_out = [CreditEntryOut.model_validate(entry) for entry in entries]
            return StandardResponse(
                status=True,
                message=CreditEntryMessages.RETRIEVED_ALL_SUCCESS.format(count=len(entries)),
                data=entries_out
            )
        except Exception as e:
            logger.exception(CreditEntryMessages.RETRIEVE_ALL_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=CreditEntryMessages.INTERNAL_SERVER_ERROR
            )

    async def get_credit_entry(self, entry_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(AICreditEntries).where(AICreditEntries.credit_entry_id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                logger.error(CreditEntryMessages.NOT_FOUND.format(id=entry_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=CreditEntryMessages.NOT_FOUND.format(id=entry_id)
                )
            logger.info(CreditEntryMessages.RETRIEVED_SUCCESS.format(id=entry_id))
            return StandardResponse(
                status=True,
                message=CreditEntryMessages.RETRIEVED_SUCCESS.format(id=entry_id),
                data=[CreditEntryOut.model_validate(entry)]
            )
        except Exception as e:
            logger.exception(CreditEntryMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=CreditEntryMessages.INTERNAL_SERVER_ERROR
            )

    async def update_credit_entry(self, entry_id: int, update_data: dict) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(AICreditEntries).where(AICreditEntries.credit_entry_id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                logger.error(CreditEntryMessages.NOT_FOUND.format(id=entry_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=CreditEntryMessages.NOT_FOUND.format(id=entry_id)
                )
            for key, value in update_data.items():
                setattr(entry, key, value)
            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)
            logger.info(CreditEntryMessages.UPDATED_SUCCESS.format(id=entry_id))
            return StandardResponse(
                status=True,
                message=CreditEntryMessages.UPDATED_SUCCESS.format(id=entry_id),
                data=[CreditEntryOut.model_validate(entry)]
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(CreditEntryMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=CreditEntryMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_credit_entry(self, entry_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(AICreditEntries).where(AICreditEntries.credit_entry_id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                logger.error(CreditEntryMessages.NOT_FOUND.format(id=entry_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=CreditEntryMessages.NOT_FOUND.format(id=entry_id)
                )
            await self.db.delete(entry)
            await self.db.commit()
            logger.info(CreditEntryMessages.DELETED_SUCCESS.format(id=entry_id))
            return StandardResponse(
                status=True,
                message=CreditEntryMessages.DELETED_SUCCESS.format(id=entry_id)
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(CreditEntryMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=CreditEntryMessages.INTERNAL_SERVER_ERROR
            )
