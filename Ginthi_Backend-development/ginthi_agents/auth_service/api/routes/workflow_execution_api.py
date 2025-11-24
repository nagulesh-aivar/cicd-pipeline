# ginthi_agents/auth_service/api/routes/workflow_execution_api.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.workflow_execution_crud import WorkflowExecutionService
from auth_service.schemas.pydantic_schema.workflow_schemas import WorkflowExecutionCreate, WorkflowExecutionUpdate
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/executions",
    tags=["Workflow Executions"],
    responses={
        404: {"description": "Execution not found"},
        500: {"description": "Internal server error"},
    },
)


def get_workflow_execution_service(db: AsyncSession = Depends(get_db)) -> WorkflowExecutionService:
    """Dependency injection for WorkflowExecutionService"""
    return WorkflowExecutionService(db)


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workflow execution",
    description="Record a new execution instance for a workflow."
)
async def create_execution(
    execution: WorkflowExecutionCreate,
    service: WorkflowExecutionService = Depends(get_workflow_execution_service)
):
    """Create a new workflow execution"""
    return await service.create_execution(**execution.dict())


@router.get(
    "/{execution_id}",
    response_model=StandardResponse,
    summary="Retrieve a workflow execution by ID",
    description="Fetch details of a workflow execution using its unique ID."
)
async def get_execution(
    execution_id: int,
    service: WorkflowExecutionService = Depends(get_workflow_execution_service)
):
    """Get a workflow execution by ID"""
    return await service.get_execution(execution_id)


@router.put(
    "/{execution_id}",
    response_model=StandardResponse,
    summary="Update a workflow execution",
    description="Update status, duration, or other details of a workflow execution."
)
async def update_execution(
    execution_id: int,
    updates: WorkflowExecutionUpdate,
    service: WorkflowExecutionService = Depends(get_workflow_execution_service)
):
    """Update an existing workflow execution"""
    return await service.update_execution(execution_id, **updates.dict(exclude_unset=True))


@router.delete(
    "/{execution_id}",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a workflow execution",
    description="Permanently remove a workflow execution using its unique ID."
)
async def delete_execution(
    execution_id: int,
    service: WorkflowExecutionService = Depends(get_workflow_execution_service)
):
    """Delete a workflow execution by ID"""
    return await service.delete_execution(execution_id)
