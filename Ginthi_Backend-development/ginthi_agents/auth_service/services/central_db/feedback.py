from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth_service.schemas.central_db.feedback_models import Feedback
from auth_service.schemas.pydantic_schema.feedback_schemas import FeedbackOut
from auth_service.utils.response_schema import StandardResponse
from auth_service.api.constants.status_codes import StatusCode
from auth_service.api.constants.messages import FeedbackMessages
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class FeedbackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_feedback(self, **kwargs) -> StandardResponse:
        try:
            feedback = Feedback(**kwargs)
            self.db.add(feedback)
            await self.db.commit()
            await self.db.refresh(feedback)
            logger.info(FeedbackMessages.CREATED_SUCCESS.format(id=feedback.feedback_id))
            return StandardResponse(
                status=True,
                message=FeedbackMessages.CREATED_SUCCESS.format(id=feedback.feedback_id),
                data=[FeedbackOut.model_validate(feedback)]
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(FeedbackMessages.CREATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=FeedbackMessages.INTERNAL_SERVER_ERROR
            )

    async def get_feedback(self, feedback_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Feedback).where(Feedback.feedback_id == feedback_id)
            )
            feedback = result.scalar_one_or_none()
            if not feedback:
                logger.warning(FeedbackMessages.NOT_FOUND.format(id=feedback_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=FeedbackMessages.NOT_FOUND.format(id=feedback_id)
                )
            logger.info(FeedbackMessages.RETRIEVED_SUCCESS.format(id=feedback_id))
            return StandardResponse(
                status=True,
                message=FeedbackMessages.RETRIEVED_SUCCESS.format(id=feedback_id),
                data=[FeedbackOut.model_validate(feedback)]
            )
        except Exception as e:
            logger.exception(FeedbackMessages.RETRIEVE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=FeedbackMessages.INTERNAL_SERVER_ERROR
            )

    async def get_feedbacks(self, skip: int = 0, limit: int = 100) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Feedback).offset(skip).limit(limit)
            )
            feedbacks = result.scalars().all()
            logger.info(FeedbackMessages.RETRIEVED_ALL_SUCCESS.format(count=len(feedbacks)))
            return StandardResponse(
                status=True,
                message=FeedbackMessages.RETRIEVED_ALL_SUCCESS.format(count=len(feedbacks)),
                data=[FeedbackOut.model_validate(fb) for fb in feedbacks]
            )
        except Exception as e:
            logger.exception(FeedbackMessages.RETRIEVE_ALL_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=FeedbackMessages.INTERNAL_SERVER_ERROR
            )

    async def update_feedback(self, feedback_id: int, data: dict) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Feedback).where(Feedback.feedback_id == feedback_id)
            )
            feedback = result.scalar_one_or_none()
            if not feedback:
                logger.warning(FeedbackMessages.NOT_FOUND.format(id=feedback_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=FeedbackMessages.NOT_FOUND.format(id=feedback_id)
                )
            for key, value in data.items():
                setattr(feedback, key, value)
            self.db.add(feedback)
            await self.db.commit()
            await self.db.refresh(feedback)
            logger.info(FeedbackMessages.UPDATED_SUCCESS.format(id=feedback_id))
            return StandardResponse(
                status=True,
                message=FeedbackMessages.UPDATED_SUCCESS.format(id=feedback_id),
                data=[FeedbackOut.model_validate(feedback)]
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(FeedbackMessages.UPDATE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=FeedbackMessages.INTERNAL_SERVER_ERROR
            )

    async def delete_feedback(self, feedback_id: int) -> StandardResponse:
        try:
            result = await self.db.execute(
                select(Feedback).where(Feedback.feedback_id == feedback_id)
            )
            feedback = result.scalar_one_or_none()
            if not feedback:
                logger.warning(FeedbackMessages.NOT_FOUND.format(id=feedback_id))
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=FeedbackMessages.NOT_FOUND.format(id=feedback_id)
                )
            await self.db.delete(feedback)
            await self.db.commit()
            logger.info(FeedbackMessages.DELETED_SUCCESS.format(id=feedback_id))
            return StandardResponse(
                status=True,
                message=FeedbackMessages.DELETED_SUCCESS.format(id=feedback_id)
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(FeedbackMessages.DELETE_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=FeedbackMessages.INTERNAL_SERVER_ERROR
            )
