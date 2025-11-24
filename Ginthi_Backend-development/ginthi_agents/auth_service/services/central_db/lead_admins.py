from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.client_models import LeadAdmins
from auth_service.schemas.pydantic_schema.client_schemas import LeadAdminOut
from typing import List
import logging
from fastapi import HTTPException
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import LeadAdminMessages
from auth_service.utils.response_schema import StandardResponse

logger = logging.getLogger(__name__)

class LeadAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_lead_admin(self, **kwargs) -> StandardResponse:
        try:
            lead_admin = LeadAdmins(**kwargs)
            self.db.add(lead_admin)
            await self.db.commit()
            await self.db.refresh(lead_admin)
            logger.info(
                LeadAdminMessages.CREATED_SUCCESS.format(
                    id=lead_admin.lead_admin_id, name=lead_admin.name, email=lead_admin.email
                )
            )
            return StandardResponse(
                status=True,
                message=LeadAdminMessages.CREATED_SUCCESS.format(
                    id=lead_admin.lead_admin_id, name=lead_admin.name, email=lead_admin.email
                ),
                data=[LeadAdminOut.model_validate(lead_admin)]
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(LeadAdminMessages.CREATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=LeadAdminMessages.INTERNAL_SERVER_ERROR
            )

    async def get_lead_admin_by_id(self, lead_admin_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(LeadAdmins).where(LeadAdmins.lead_admin_id == lead_admin_id)
            )
            lead_admin = result.scalar_one_or_none()
            if not lead_admin:
                logger.warning(LeadAdminMessages.NOT_FOUND.format(id=lead_admin_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=LeadAdminMessages.NOT_FOUND.format(id=lead_admin_id)
                )
            logger.info(
                LeadAdminMessages.RETRIEVED_SUCCESS.format(
                    id=lead_admin_id, name=lead_admin.name, email=lead_admin.email
                )
            )
            return StandardResponse(
                status=True,
                message=LeadAdminMessages.RETRIEVED_SUCCESS.format(
                    id=lead_admin_id, name=lead_admin.name, email=lead_admin.email
                ),
                data=[LeadAdminOut.model_validate(lead_admin)]
            )
        except Exception as e:
            logger.exception(LeadAdminMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=LeadAdminMessages.INTERNAL_SERVER_ERROR
            )

    async def get_all_lead_admins(self) -> StandardResponse:
        try:
            result = await self.db.execute(select(LeadAdmins))
            lead_admins = result.scalars().all()
            logger.info(LeadAdminMessages.RETRIEVED_ALL_SUCCESS)
            return StandardResponse(
                status=True,
                message=LeadAdminMessages.RETRIEVED_ALL_SUCCESS,
                data=[LeadAdminOut.model_validate(la) for la in lead_admins]
            )
        except Exception as e:
            logger.exception(LeadAdminMessages.RETRIEVE_ALL_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=LeadAdminMessages.INTERNAL_SERVER_ERROR
            )

    async def update_lead_admin(self, lead_admin_id: int, **kwargs) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(LeadAdmins).where(LeadAdmins.lead_admin_id == lead_admin_id)
            )
            lead_admin = result.scalar_one_or_none()
            if not lead_admin:
                logger.warning(LeadAdminMessages.NOT_FOUND.format(id=lead_admin_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=LeadAdminMessages.NOT_FOUND.format(id=lead_admin_id)
                )
            for key, value in kwargs.items():
                setattr(lead_admin, key, value)
            self.db.add(lead_admin)
            await self.db.commit()
            await self.db.refresh(lead_admin)
            logger.info(
                LeadAdminMessages.UPDATED_SUCCESS.format(
                    id=lead_admin_id, name=lead_admin.name, email=lead_admin.email
                )
            )
            return StandardResponse(
                status=True,
                message=LeadAdminMessages.UPDATED_SUCCESS.format(
                    id=lead_admin_id, name=lead_admin.name, email=lead_admin.email
                ),
                data=[LeadAdminOut.model_validate(lead_admin)]
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(LeadAdminMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=LeadAdminMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_lead_admin(self, lead_admin_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(LeadAdmins).where(LeadAdmins.lead_admin_id == lead_admin_id)
            )
            lead_admin = result.scalar_one_or_none()
            if not lead_admin:
                logger.warning(LeadAdminMessages.NOT_FOUND.format(id=lead_admin_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=LeadAdminMessages.NOT_FOUND.format(id=lead_admin_id)
                )
            await self.db.delete(lead_admin)
            await self.db.commit()
            logger.info(LeadAdminMessages.DELETED_SUCCESS.format(id=lead_admin_id))
            return StandardResponse(
                status=True,
                message=LeadAdminMessages.DELETED_SUCCESS.format(id=lead_admin_id)
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(LeadAdminMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=LeadAdminMessages.INTERNAL_SERVER_ERROR
            )
