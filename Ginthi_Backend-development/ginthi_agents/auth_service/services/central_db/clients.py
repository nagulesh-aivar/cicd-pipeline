from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.client_models import Clients
from auth_service.schemas.pydantic_schema.client_schemas import ClientOut
from fastapi import HTTPException
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import ClientMessages
from auth_service.utils.response_schema import StandardResponse
import logging

logger = logging.getLogger(__name__)

class ClientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_client(self, **kwargs) -> StandardResponse:
        try:
            client = Clients(**kwargs)
            self.db.add(client)
            await self.db.commit()
            await self.db.refresh(client)
            logger.info(ClientMessages.CREATED_SUCCESS.format(id=client.client_id, name=client.name))
            client_out = [ClientOut.model_validate(client)]
            return StandardResponse(
                status=True,
                message=ClientMessages.CREATED_SUCCESS.format(id=client.client_id, name=client.name),
                data=client_out
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientMessages.CREATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientMessages.INTERNAL_SERVER_ERROR
            )

    async def get_clients(self, skip: int = 0, limit: int = 100) -> StandardResponse:
        try:
            result = await self.db.execute(
               select(Clients).offset(skip).limit(limit)
            )
            clients = result.scalars().all()
            logger.info(ClientMessages.RETRIEVED_ALL_SUCCESS.format(count=len(clients)))
            clients_out = [ClientOut.model_validate(client) for client in clients]
            return StandardResponse(
                status=True,
                message=ClientMessages.RETRIEVED_ALL_SUCCESS.format(count=len(clients)),
                data=clients_out
            )
        except Exception as e:
            logger.exception(ClientMessages.RETRIEVE_ALL_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientMessages.INTERNAL_SERVER_ERROR
            )

    async def get_client(self, client_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
            select(Clients).where(Clients.client_id == client_id)
            )
            client = result.scalar_one_or_none()
            if not client:
                logger.error(ClientMessages.NOT_FOUND.format(id=client_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientMessages.NOT_FOUND.format(id=client_id)
                )
            logger.info(ClientMessages.RETRIEVED_SUCCESS.format(id=client_id, name=client.name))
            client_out = [ClientOut.model_validate(client)]
            return StandardResponse(
                status=True,
                message=ClientMessages.RETRIEVED_SUCCESS.format(id=client_id, name=client.name),
                data=client_out
            )
        except Exception as e:
            logger.exception(ClientMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientMessages.INTERNAL_SERVER_ERROR
            )

    async def update_client(self, client_id: int, update_data: dict) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Clients).where(Clients.client_id == client_id)
            )
            client = result.scalar_one_or_none()
            if not client:
                logger.error(ClientMessages.NOT_FOUND.format(id=client_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientMessages.NOT_FOUND.format(id=client_id)
                )
            for key, value in update_data.items():
                setattr(client, key, value)
            self.db.add(client)
            await self.db.commit()
            await self.db.refresh(client)
            logger.info(ClientMessages.UPDATED_SUCCESS.format(id=client_id, name=client.name))
            return StandardResponse(
                status=True,
                message=ClientMessages.UPDATED_SUCCESS.format(id=client_id, name=client.name),
                data=[ClientOut.model_validate(client)]
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_client(self, client_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Clients).where(Clients.client_id == client_id)
            )
            client = result.scalar_one_or_none()
            if not client:
                logger.error(ClientMessages.NOT_FOUND.format(id=client_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientMessages.NOT_FOUND.format(id=client_id)
                )
            await self.db.delete(client)
            await self.db.commit()
            logger.info(ClientMessages.DELETED_SUCCESS.format(id=client_id))
            return StandardResponse(
                status=True,
                message=ClientMessages.DELETED_SUCCESS.format(id=client_id)
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientMessages.INTERNAL_SERVER_ERROR
            )
