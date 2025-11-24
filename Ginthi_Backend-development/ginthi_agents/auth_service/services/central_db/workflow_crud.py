from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.workflow_models import Workflows
from auth_service.schemas.pydantic_schema.workflow_schemas import WorkflowOut
from auth_service.utils.response_schema import StandardResponse
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import WorkflowMessages
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workflow(self, **kwargs) -> StandardResponse:
        try:
            workflow = Workflows(**kwargs)
            self.db.add(workflow)
            await self.db.commit()
            await self.db.refresh(workflow)
            logger.info(WorkflowMessages.CREATED_SUCCESS.format(id=workflow.workflow_id))
            workflow_out = [WorkflowOut.model_validate(workflow)]
            return StandardResponse(
                status=True,
                message=WorkflowMessages.CREATED_SUCCESS.format(id=workflow.workflow_id),
                data=workflow_out
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(WorkflowMessages.CREATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowMessages.INTERNAL_SERVER_ERROR
            )

    async def get_workflows(self, skip: int = 0, limit: int = 100) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Workflows).offset(skip).limit(limit)
            )
            workflows = result.scalars().all()
            logger.info(WorkflowMessages.RETRIEVED_ALL_SUCCESS.format(count=len(workflows)))
            workflows_out = [WorkflowOut.model_validate(w) for w in workflows]
            return StandardResponse(
                status=True,
                message=WorkflowMessages.RETRIEVED_ALL_SUCCESS.format(count=len(workflows)),
                data=workflows_out
            )
        except Exception as e:
            logger.exception(WorkflowMessages.RETRIEVE_ALL_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowMessages.INTERNAL_SERVER_ERROR
            )

    async def get_workflow(self, workflow_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Workflows).where(Workflows.workflow_id == workflow_id)
            )
            workflow = result.scalar_one_or_none()
            if not workflow:
                logger.error(WorkflowMessages.NOT_FOUND.format(id=workflow_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=WorkflowMessages.NOT_FOUND.format(id=workflow_id)
                )
            logger.info(WorkflowMessages.RETRIEVED_SUCCESS.format(id=workflow_id))
            workflow_out = [WorkflowOut.model_validate(workflow)]
            return StandardResponse(
                status=True,
                message=WorkflowMessages.RETRIEVED_SUCCESS.format(id=workflow_id),
                data=workflow_out
            )
        except Exception as e:
            logger.exception(WorkflowMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowMessages.INTERNAL_SERVER_ERROR
            )

    async def update_workflow(self, workflow_id: int, data: dict) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Workflows).where(Workflows.workflow_id == workflow_id)
            )
            workflow = result.scalar_one_or_none()
            if not workflow:
                logger.error(WorkflowMessages.NOT_FOUND.format(id=workflow_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=WorkflowMessages.NOT_FOUND.format(id=workflow_id)
                )
            for key, value in data.items():
                setattr(workflow, key, value)
            self.db.add(workflow)
            await self.db.commit()
            await self.db.refresh(workflow)
            logger.info(WorkflowMessages.UPDATED_SUCCESS.format(id=workflow_id))
            workflow_out = [WorkflowOut.model_validate(workflow)]
            return StandardResponse(
                status=True,
                message=WorkflowMessages.UPDATED_SUCCESS.format(id=workflow_id),
                data=workflow_out
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(WorkflowMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_workflow(self, workflow_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Workflows).where(Workflows.workflow_id == workflow_id)
            )
            workflow = result.scalar_one_or_none()
            if not workflow:
                logger.error(WorkflowMessages.NOT_FOUND.format(id=workflow_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=WorkflowMessages.NOT_FOUND.format(id=workflow_id)
                )
            await self.db.delete(workflow)
            await self.db.commit()
            logger.info(WorkflowMessages.DELETED_SUCCESS.format(id=workflow_id))
            return StandardResponse(
                status=True,
                message=WorkflowMessages.DELETED_SUCCESS.format(id=workflow_id)
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(WorkflowMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowMessages.INTERNAL_SERVER_ERROR
            )
