from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.server_models import ClientServers
from auth_service.schemas.pydantic_schema.server_schemas import ClientServerOut
from auth_service.utils.response_schema import StandardResponse
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import ClientServerMessages
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class ClientServerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_server(self, **kwargs) -> StandardResponse:
        try:
            server = ClientServers(**kwargs)
            self.db.add(server)
            await self.db.commit()
            await self.db.refresh(server)
            logger.info(
                ClientServerMessages.CREATED_SUCCESS.format(
                    id=server.server_id, name=server.server_name
                )
            )
            server_out = [ClientServerOut.model_validate(server)]
            return StandardResponse(
                status=True,
                message=ClientServerMessages.CREATED_SUCCESS.format(
                    id=server.server_id, name=server.server_name
                ),
                data=server_out
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientServerMessages.CREATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientServerMessages.INTERNAL_SERVER_ERROR
            )

    async def get_server(self, server_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(ClientServers).where(ClientServers.server_id == server_id)
            )
            server = result.scalar_one_or_none()
            if not server:
                logger.warning(ClientServerMessages.NOT_FOUND.format(id=server_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientServerMessages.NOT_FOUND.format(id=server_id)
                )
            logger.info(
                ClientServerMessages.RETRIEVED_SUCCESS.format(
                    id=server_id, name=server.server_name
                )
            )
            server_out = [ClientServerOut.model_validate(server)]
            return StandardResponse(
                status=True,
                message=ClientServerMessages.RETRIEVED_SUCCESS.format(
                    id=server_id, name=server.server_name
                ),
                data=server_out
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(ClientServerMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientServerMessages.INTERNAL_SERVER_ERROR
            )

    async def update_server(self, server_id: int, **kwargs) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(ClientServers).where(ClientServers.server_id == server_id)
            )
            server = result.scalar_one_or_none()
            if not server:
                logger.warning(ClientServerMessages.NOT_FOUND.format(id=server_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientServerMessages.NOT_FOUND.format(id=server_id)
                )
            for key, value in kwargs.items():
                setattr(server, key, value)
            self.db.add(server)
            await self.db.commit()
            await self.db.refresh(server)
            logger.info(
                ClientServerMessages.UPDATED_SUCCESS.format(
                    id=server_id, name=server.server_name
                )
            )
            server_out = [ClientServerOut.model_validate(server)]
            return StandardResponse(
                status=True,
                message=ClientServerMessages.UPDATED_SUCCESS.format(
                    id=server_id, name=server.server_name
                ),
                data=server_out
            )
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientServerMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientServerMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_server(self, server_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(ClientServers).where(ClientServers.server_id == server_id)
            )
            server = result.scalar_one_or_none()
            if not server:
                logger.warning(ClientServerMessages.NOT_FOUND.format(id=server_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=ClientServerMessages.NOT_FOUND.format(id=server_id)
                )
            await self.db.delete(server)
            await self.db.commit()
            logger.info(ClientServerMessages.DELETED_SUCCESS.format(id=server_id))
            return StandardResponse(
                status=True,
                message=ClientServerMessages.DELETED_SUCCESS.format(id=server_id),
                data=None
            )
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(ClientServerMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=ClientServerMessages.INTERNAL_SERVER_ERROR
            )
