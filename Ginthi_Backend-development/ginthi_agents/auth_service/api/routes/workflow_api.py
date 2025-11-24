from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.db.postgres_db import get_db
from auth_service.services.central_db.workflow_crud import WorkflowService
from auth_service.schemas.pydantic_schema.workflow_schemas import WorkflowCreate, WorkflowUpdate
from auth_service.utils.response_schema import StandardResponse

router = APIRouter(
    prefix="/workflows",
    tags=["Workflows"],
    responses={
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"},
    },
)


def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    """Dependency injection for WorkflowService"""
    return WorkflowService(db)


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workflow",
    description="Create a new workflow in the system. Use this endpoint when adding a workflow."
)
async def create_workflow(
    workflow: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service)
):
    """Create a new workflow"""
    return await service.create_workflow(**workflow.dict())


@router.get(
    "/{workflow_id}",
    response_model=StandardResponse,
    summary="Retrieve a workflow by ID",
    description="Fetch details of a workflow using its unique ID."
)
async def get_workflow(
    workflow_id: int,
    service: WorkflowService = Depends(get_workflow_service)
):
    """Get a workflow by ID"""
    return await service.get_workflow(workflow_id)


@router.get(
    "/",
    response_model=StandardResponse,
    summary="List all workflows",
    description="Retrieve a paginated list of all workflows. Use optional `skip` and `limit` parameters for pagination."
)
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    service: WorkflowService = Depends(get_workflow_service)
):
    """List workflows with pagination"""
    return await service.get_workflows(skip=skip, limit=limit)


@router.put(
    "/{workflow_id}",
    response_model=StandardResponse,
    summary="Update a workflow",
    description="Update workflow details such as name, description, or settings."
)
async def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    service: WorkflowService = Depends(get_workflow_service)
):
    """Update an existing workflow"""
    return await service.update_workflow(workflow_id, workflow_update.dict(exclude_unset=True))


@router.delete(
    "/{workflow_id}",
    response_model=StandardResponse,
    summary="Delete a workflow",
    description="Permanently remove a workflow from the system using its unique ID."
)
async def delete_workflow(
    workflow_id: int,
    service: WorkflowService = Depends(get_workflow_service)
):
    """Delete a workflow by ID"""
    return await service.delete_workflow(workflow_id)
