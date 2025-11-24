from fastapi import APIRouter, status, Depends
from typing import List, Optional

from client_service.schemas.pydantic_schemas import (
    WorkflowExecutionLogCreate
)
from client_service.schemas.base_response import APIResponse
from client_service.services.workflow_executionlog_service import WorkflowExecutionLogService

router = APIRouter()

# Dependency injection
def get_workflow_executionlog_service() -> WorkflowExecutionLogService:
    return WorkflowExecutionLogService()

# ─────────────────────────────
# CREATE LOG
# ─────────────────────────────
@router.post(
    "/",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workflow execution log",
    description="Creates a new workflow execution log to track the run status, inputs, and outputs of a workflow execution."
)
async def create_log(
    log_data: WorkflowExecutionLogCreate,
    service: WorkflowExecutionLogService = Depends(get_workflow_executionlog_service)
):
    return await service.create_log(log_data)

# ─────────────────────────────
# GET ALL LOGS
# ─────────────────────────────
@router.get(
    "/",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all workflow execution logs",
    description="Fetches all workflow execution logs with pagination support using `skip` and `limit` parameters."
)
async def get_all_logs(skip: int = 0, limit: int = 100,
    service: WorkflowExecutionLogService = Depends(get_workflow_executionlog_service)
):
    return await service.get_all_logs(skip, limit)

# ─────────────────────────────
# SEARCH LOGS - ONE OR TWO COLUMNS (OPTIONAL)
# ─────────────────────────────
@router.get(
    "/search",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Search workflow execution logs by one or two columns (optional)",
    description="Search logs using fuzzy matching on one or two fields simultaneously within a specific central workflow. Provide at least the central_workflow_id; column/value pairs are optional for filtering."
)
async def search_logs(
    central_workflow_id: str,
    column1: Optional[str] = None,
    value1: Optional[str] = None,
    column2: Optional[str] = None,
    value2: Optional[str] = None,
    threshold: int = 80,
    top_n: int = 10,
    service: WorkflowExecutionLogService = Depends(get_workflow_executionlog_service)
):
    """
    Search workflow execution logs by one or two columns with fuzzy matching (optional parameters)
    
    Args:
        column1: Optional first field name to search (e.g., "source_trigger")
        value1: Optional value to search for in column1
        column2: Optional second field name to search (e.g., "created_by")
        value2: Optional value to search for in column2
        central_workflow_id: Required central workflow ID to filter results
        threshold: Minimum match score (0-100), default 80
        top_n: Maximum number of results, default 10
        
    Examples:
    - Single column: /search?column1=source_trigger&value1=api&central_workflow_id=abc123
    - Two columns: /search?column1=source_trigger&value1=api&column2=created_by&value2=john&central_workflow_id=abc123
    - All logs in central workflow: /search?central_workflow_id=abc123
    """
    return await service.search_logs(
        column1=column1,
        value1=value1,
        column2=column2,
        value2=value2,
        central_workflow_id=central_workflow_id,
        threshold=threshold,
        top_n=top_n
    )

# ─────────────────────────────
# GET LOG BY ID
# ─────────────────────────────
@router.get(
    "/{log_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workflow execution log by ID",
    description="Retrieves detailed information of a specific workflow execution log using its MongoDB ObjectId."
)
async def get_log_by_id(
    log_id: str,
    service: WorkflowExecutionLogService = Depends(get_workflow_executionlog_service)
):
    return await service.get_log_by_id(log_id)


# ─────────────────────────────
# UPDATE LOG
# ─────────────────────────────
@router.put(
    "/{log_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Update workflow execution log",
    description="Updates the status, result, or metadata of an existing workflow execution log by its ObjectId."
)
async def update_log(
    log_id: str,
    log_data: dict,
    service: WorkflowExecutionLogService = Depends(get_workflow_executionlog_service)
):
    return await service.update_log(log_id, log_data)

# ─────────────────────────────
# DELETE LOG
# ─────────────────────────────
@router.delete(
    "/{log_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete workflow execution log",
    description="Delete a workflow execution log permanently by ID"
)
async def delete_log(
    log_id: str,
    service: WorkflowExecutionLogService = Depends(get_workflow_executionlog_service)
):
    return await service.delete_log(log_id)
