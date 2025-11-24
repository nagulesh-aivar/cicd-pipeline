from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.client_models import ClientAPIKeys
from auth_service.schemas.pydantic_schema.client_schemas import ClientAPIKeyOut
from fastapi import HTTPException
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import ClientAPIKeyMessages
from auth_service.utils.response_schema import StandardResponse
import logging

logger = logging.getLogger(__name__)


class ClientAPIKeyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_api_key(self, **kwargs) -> StandardResponse:
        """Create a new API key"""
        try:
            api_key = ClientAPIKeys(**kwargs)
            self.db.add(api_key)
            await self.db.commit()
            await self.db.refresh(api_key)
            logger.info(ClientAPIKeyMessages.CREATED_SUCCESS.format(id=api_key.api_key_id))
            return StandardResponse(
                status=True,
                message=ClientAPIKeyMessages.CREATED_SUCCESS.format(id=api_key.api_key_id),
                data=[ClientAPIKeyOut.model_validate(api_key)]
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientAPIKeyMessages.CREATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientAPIKeyMessages.INTERNAL_SERVER_ERROR
            )

    async def get_api_keys(self, skip: int = 0, limit: int = 100) -> StandardResponse:
        """Retrieve a list of API keys with pagination"""
        try:
            result = await self.db.execute(
                select(ClientAPIKeys).offset(skip).limit(limit)
            )
            api_keys = result.scalars().all()
            logger.info(ClientAPIKeyMessages.RETRIEVED_ALL_SUCCESS.format(count=len(api_keys)))
            api_keys_out = [ClientAPIKeyOut.model_validate(api_key) for api_key in api_keys]
            return StandardResponse(
                status=True,
                message=ClientAPIKeyMessages.RETRIEVED_ALL_SUCCESS.format(count=len(api_keys)),
                data=api_keys_out
            )
        except Exception as e:
            logger.exception(ClientAPIKeyMessages.RETRIEVE_ALL_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientAPIKeyMessages.INTERNAL_SERVER_ERROR
            )

    async def get_api_key(self, api_key_id: int) -> StandardResponse:
        """Retrieve a single API key by ID"""
        try:
            result = await self.db.execute(
                select(ClientAPIKeys).where(ClientAPIKeys.api_key_id == api_key_id)
            )
            api_key = result.scalar_one_or_none()
            if not api_key:
                logger.error(ClientAPIKeyMessages.NOT_FOUND.format(id=api_key_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientAPIKeyMessages.NOT_FOUND.format(id=api_key_id)
                )
            logger.info(ClientAPIKeyMessages.RETRIEVED_SUCCESS.format(id=api_key_id))
            return StandardResponse(
                status=True,
                message=ClientAPIKeyMessages.RETRIEVED_SUCCESS.format(id=api_key_id),
                data=[ClientAPIKeyOut.model_validate(api_key)]
            )
        except Exception as e:
            logger.exception(ClientAPIKeyMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientAPIKeyMessages.INTERNAL_SERVER_ERROR
            )

    async def update_api_key(self, api_key_id: int, data: dict) -> StandardResponse:
        """Update an existing API key"""
        try:
            result = await self.db.execute(
                select(ClientAPIKeys).where(ClientAPIKeys.api_key_id == api_key_id)
            )
            api_key = result.scalar_one_or_none()
            if not api_key:
                logger.error(ClientAPIKeyMessages.NOT_FOUND.format(id=api_key_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientAPIKeyMessages.NOT_FOUND.format(id=api_key_id)
                )
            for key, value in data.items():
                setattr(api_key, key, value)
            self.db.add(api_key)
            await self.db.commit()
            await self.db.refresh(api_key)
            logger.info(ClientAPIKeyMessages.UPDATED_SUCCESS.format(id=api_key_id))
            return StandardResponse(
                status=True,
                message=ClientAPIKeyMessages.UPDATED_SUCCESS.format(id=api_key_id),
                data=[ClientAPIKeyOut.model_validate(api_key)]
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientAPIKeyMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientAPIKeyMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_api_key(self, api_key_id: int) -> StandardResponse:
        """Delete an API key by ID"""
        try:
            result = await self.db.execute(
                select(ClientAPIKeys).where(ClientAPIKeys.api_key_id == api_key_id)
            )
            api_key = result.scalar_one_or_none()
            if not api_key:
                logger.error(ClientAPIKeyMessages.NOT_FOUND.format(id=api_key_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientAPIKeyMessages.NOT_FOUND.format(id=api_key_id)
                )
            await self.db.delete(api_key)
            await self.db.commit()
            logger.info(ClientAPIKeyMessages.DELETED_SUCCESS.format(id=api_key_id))
            return StandardResponse(
                status=True,
                message=ClientAPIKeyMessages.DELETED_SUCCESS.format(id=api_key_id)
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientAPIKeyMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientAPIKeyMessages.INTERNAL_SERVER_ERROR
            )
