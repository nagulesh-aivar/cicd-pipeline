from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.feedback import FeedbackService
from auth_service.schemas.pydantic_schema.feedback_schemas import FeedbackCreate, FeedbackUpdate
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
    responses={
        404: {"description": "Feedback not found"},
        500: {"description": "Internal server error"},
    },
)


def get_feedback_service(db: AsyncSession = Depends(get_db)) -> FeedbackService:
    """Dependency injection for FeedbackService"""
    return FeedbackService(db)


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feedback entry",
    description="Create a new feedback entry for a client, user, or workflow. "
                "Use this endpoint when capturing feedback data in the system."
)
async def create_feedback(
    feedback: FeedbackCreate,
    service: FeedbackService = Depends(get_feedback_service)
):
    """Create a new feedback entry"""
    return await service.create_feedback(**feedback.dict())


@router.get(
    "/",
    response_model=StandardResponse,
    summary="List feedback entries",
    description="Retrieve a paginated list of all feedback entries. "
                "Use this endpoint to fetch all client or user feedback records."
)
async def list_feedbacks(
    skip: int = 0,
    limit: int = 100,
    service: FeedbackService = Depends(get_feedback_service)
):
    """List all feedback entries with pagination"""
    return await service.get_feedbacks(skip=skip, limit=limit)


@router.get(
    "/{feedback_id}",
    response_model=StandardResponse,
    summary="Get feedback by ID",
    description="Retrieve details of a specific feedback entry by its ID. "
                "Use this endpoint to view full information about one feedback record."
)
async def get_feedback(
    feedback_id: int,
    service: FeedbackService = Depends(get_feedback_service)
):
    """Get details of a specific feedback entry"""
    return await service.get_feedback(feedback_id=feedback_id)


@router.put(
    "/{feedback_id}",
    response_model=StandardResponse,
    summary="Update a feedback entry",
    description="Update the details of an existing feedback entry. "
                "Use this endpoint to modify feedback content or related metadata."
)
async def update_feedback(
    feedback_id: int,
    feedback_update: FeedbackUpdate,
    service: FeedbackService = Depends(get_feedback_service)
):
    """Update a feedback entry"""
    return await service.update_feedback(
        feedback_id=feedback_id,
        data=feedback_update.dict(exclude_unset=True)
    )


@router.delete(
    "/{feedback_id}",
    response_model=StandardResponse,
    summary="Delete a feedback entry",
    description="Permanently delete a feedback entry by its ID. "
                "Use this endpoint to remove invalid or obsolete feedback data."
)
async def delete_feedback(
    feedback_id: int,
    service: FeedbackService = Depends(get_feedback_service)
):
    """Delete a feedback entry"""
    return await service.delete_feedback(feedback_id=feedback_id)
