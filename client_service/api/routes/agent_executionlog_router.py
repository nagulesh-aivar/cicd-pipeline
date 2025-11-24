from fastapi import APIRouter, status, Depends
from typing import List, Optional
from client_service.schemas.pydantic_schemas import (
    AgentExecutionLogCreate,
    AgentExecutionLogUpdate
)
from client_service.schemas.base_response import APIResponse
from client_service.services.agent_executionlog_service import AgentExecutionService

router = APIRouter()

# Dependency injection
def get_agent_execution_service() -> AgentExecutionService:
    return AgentExecutionService()

# ─────────────────────────────
# CREATE AGENT LOG
# ─────────────────────────────
@router.post(
    "/",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_agent_execution_log",
    summary="Create agent execution log",
    description="Creates a new record of an agent’s execution within a workflow. "
    "Use when: 'agent started a task', 'store execution result', or 'log agent output'. "
    "Includes status, process steps, user feedback, and rule-wise results."
)
async def create_agent_log(
    log_data: AgentExecutionLogCreate,
    service: AgentExecutionService = Depends(get_agent_execution_service)
):
    return await service.create_log(log_data)

# ─────────────────────────────
# GET ALL AGENT LOGS
# ─────────────────────────────
@router.get(
    "/",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all agent execution logs",
    description="Fetches all agent execution log entries across workflows and agents. "
    "Use when: 'list agent runs', 'analyze execution history', or 'generate reports'."
)
async def get_all_agent_logs(skip: int = 0, limit: int = 100,
    service: AgentExecutionService = Depends(get_agent_execution_service)
):
    return await service.get_all_logs(skip, limit)

# ─────────────────────────────
# SEARCH AGENT LOGS - ONE OR TWO COLUMNS (OPTIONAL)
# ─────────────────────────────
@router.get(
    "/search",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Search agent execution logs by one or two columns (optional)",
    description="Search logs using fuzzy matching on one or two fields simultaneously within a specific workflow. Provide at least the workflow_id; column/value pairs are optional for filtering."
)
async def search_agent_logs(
    workflow_id: str,
    column1: Optional[str] = None,
    value1: Optional[str] = None,
    column2: Optional[str] = None,
    value2: Optional[str] = None,
    threshold: int = 80,
    top_n: int = 10,
    service: AgentExecutionService = Depends(get_agent_execution_service)
):
    """
    Search agent execution logs by one or two columns with fuzzy matching (optional parameters)
    
    Args:
        column1: Optional first field name to search (e.g., "agent_id")
        value1: Optional value to search for in column1
        column2: Optional second field name to search (e.g., "status")
        value2: Optional value to search for in column2
        workflow_id: Required workflow ID to filter results
        threshold: Minimum match score (0-100), default 80
        top_n: Maximum number of results, default 10
        
    Examples:
    - Single column: /search?column1=agent_id&value1=agent123&workflow_id=abc123
    - Two columns: /search?column1=agent_id&value1=agent123&column2=status&value2=success&workflow_id=abc123
    - All logs in workflow: /search?workflow_id=abc123
    """
    return await service.search_logs(
        column1=column1,
        value1=value1,
        column2=column2,
        value2=value2,
        workflow_id=workflow_id,
        threshold=threshold,
        top_n=top_n
    )

# ─────────────────────────────
# GET AGENT LOG BY ID
# ─────────────────────────────
@router.get(
    "/{log_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_agent_execution_log_by_id",
    summary="Get agent execution log by ID",
    description= "Retrieves detailed information of a specific agent execution log by its MongoDB ObjectId. "
                 "Use when: 'view agent run details', 'check execution result', or 'debug workflow step'."
)
async def get_agent_log_by_id(
    log_id: str,
    service: AgentExecutionService = Depends(get_agent_execution_service)
):
    return await service.get_log_by_id(log_id)

# ─────────────────────────────
# GET ALL AGENT LOGS
# ─────────────────────────────
@router.get(
    "/",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_all_agent_execution_logs",
    summary="Get all agent execution logs",
    description="Fetches all agent execution log entries across workflows and agents. "
    "Use when: 'list agent runs', 'analyze execution history', or 'generate reports'."
)
async def get_all_agent_logs(skip: int = 0, limit: int = 100,
    service: AgentExecutionService = Depends(get_agent_execution_service)
):
    return await service.get_all_logs(skip, limit)

# ─────────────────────────────
# UPDATE AGENT LOG
# ─────────────────────────────
@router.put(
    "/{log_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_agent_execution_log",
    summary="Update agent execution log",
    description="Updates the details of an existing agent execution log. "
    "Use when: 'correct log status', 'add user feedback', or 'update error/output details'."
)
async def update_agent_log(
    log_id: str,
    log_data: AgentExecutionLogUpdate,
    service: AgentExecutionService = Depends(get_agent_execution_service)
):
    return await service.update_log(log_id, log_data)

# ─────────────────────────────
# DELETE AGENT LOG
# ─────────────────────────────
@router.delete(
    "/{log_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    operation_id="delete_agent_execution_log",
    summary="Delete agent execution log",
    description="Deletes an existing agent execution log permanently. "
    "Use when: 'remove invalid entries' or 'clean up workflow logs'."
)
async def delete_agent_log(
    log_id: str,
    service: AgentExecutionService = Depends(get_agent_execution_service)
):
    return await service.delete_log(log_id)
