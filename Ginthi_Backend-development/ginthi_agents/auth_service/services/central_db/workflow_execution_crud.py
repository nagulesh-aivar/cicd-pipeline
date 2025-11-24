from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.workflow_models import WorkflowExecutions
from auth_service.schemas.pydantic_schema.workflow_schemas import WorkflowExecutionOut
from auth_service.utils.response_schema import StandardResponse
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import WorkflowExecutionMessages
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class WorkflowExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_execution(self, **kwargs) -> StandardResponse:
        try:
            execution = WorkflowExecutions(**kwargs)
            self.db.add(execution)
            await self.db.commit()
            await self.db.refresh(execution)
            logger.info(WorkflowExecutionMessages.CREATED_SUCCESS.format(id=execution.execution_id))
            execution_out = [WorkflowExecutionOut.model_validate(execution)]
            return StandardResponse(
                status=True,
                message=WorkflowExecutionMessages.CREATED_SUCCESS.format(id=execution.execution_id),
                data=execution_out
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(WorkflowExecutionMessages.CREATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowExecutionMessages.INTERNAL_SERVER_ERROR
            )

    async def get_execution(self, execution_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(WorkflowExecutions).where(WorkflowExecutions.execution_id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if not execution:
                logger.warning(WorkflowExecutionMessages.NOT_FOUND.format(id=execution_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=WorkflowExecutionMessages.NOT_FOUND.format(id=execution_id)
                )
            logger.info(WorkflowExecutionMessages.RETRIEVED_SUCCESS.format(id=execution_id))
            execution_out = [WorkflowExecutionOut.model_validate(execution)]
            return StandardResponse(
                status=True,
                message=WorkflowExecutionMessages.RETRIEVED_SUCCESS.format(id=execution_id),
                data=execution_out
            )
        except Exception as e:
            logger.exception(WorkflowExecutionMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowExecutionMessages.INTERNAL_SERVER_ERROR
            )

    async def update_execution(self, execution_id: int, **kwargs) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(WorkflowExecutions).where(WorkflowExecutions.execution_id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if not execution:
                logger.warning(WorkflowExecutionMessages.NOT_FOUND.format(id=execution_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=WorkflowExecutionMessages.NOT_FOUND.format(id=execution_id)
                )
            for key, value in kwargs.items():
                setattr(execution, key, value)
            self.db.add(execution)
            await self.db.commit()
            await self.db.refresh(execution)
            logger.info(WorkflowExecutionMessages.UPDATED_SUCCESS.format(id=execution_id))
            execution_out = [WorkflowExecutionOut.model_validate(execution)]
            return StandardResponse(
                status=True,
                message=WorkflowExecutionMessages.UPDATED_SUCCESS.format(id=execution_id),
                data=execution_out
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(WorkflowExecutionMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowExecutionMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_execution(self, execution_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(WorkflowExecutions).where(WorkflowExecutions.execution_id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if not execution:
                logger.warning(WorkflowExecutionMessages.NOT_FOUND.format(id=execution_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=WorkflowExecutionMessages.NOT_FOUND.format(id=execution_id)
                )
            await self.db.delete(execution)
            await self.db.commit()
            logger.info(WorkflowExecutionMessages.DELETED_SUCCESS.format(id=execution_id))
            return StandardResponse(
                status=True,
                message=WorkflowExecutionMessages.DELETED_SUCCESS.format(id=execution_id)
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(WorkflowExecutionMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=WorkflowExecutionMessages.INTERNAL_SERVER_ERROR
            )
