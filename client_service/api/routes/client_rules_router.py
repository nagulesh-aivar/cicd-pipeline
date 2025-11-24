from fastapi import APIRouter, status, Depends
from typing import List, Optional

from client_service.schemas.pydantic_schemas import (
    ClientRuleCreate,
    ClientRuleUpdate
)
from client_service.schemas.base_response import APIResponse
from client_service.services.client_rules_service import ClientRulesService

router = APIRouter()

# Dependency injection for the service
def get_client_rules_service() -> ClientRulesService:
    return ClientRulesService()

# ─────────────────────────────
# CREATE RULE
# ─────────────────────────────
@router.post(
    "/create",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new client rule",
    description="Adds a new client rule for workflow automation or validation logic."
)
async def create_rule(
    rule_data: ClientRuleCreate,
    service: ClientRulesService = Depends(get_client_rules_service)
):
    """Create a new client rule"""
    return await service.create_rule(rule_data)

# ─────────────────────────────
# GET ALL RULES
# ─────────────────────────────
@router.get(
    "/",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all client rules",
    description="Fetches all client rules with pagination support using `skip` and `limit` parameters."
)
async def get_all_rules(skip: int = 0, limit: int = 100,
    service: ClientRulesService = Depends(get_client_rules_service)
):
    """Get all client rules"""
    return await service.get_all_rules(skip, limit)

# ─────────────────────────────
# SEARCH RULES - TWO COLUMNS
# ─────────────────────────────
@router.get(
    "/search",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    operation_id="search_client_rules",
    summary="Search client rules with fuzzy matching",
    description="Searches client rules within a specific workflow using fuzzy text matching on up to two fields simultaneously. "
    "Use when: 'find rules by name', 'search rules by category', or 'locate rules matching specific criteria'. "
    "Supports flexible search with configurable similarity threshold and result limits. "
    "Returns rules ranked by match score with optional dual-column filtering."
)
async def search_rules(
    client_workflow_id: str,
    column1: Optional[str] = None,
    value1: Optional[str] = None,
    column2: Optional[str] = None,
    value2: Optional[str] = None,
    threshold: int = 80,
    top_n: int = 10,
    service: ClientRulesService = Depends(get_client_rules_service)
):
    """
    Search client rules by up to two columns with fuzzy matching.
    
    Performs fuzzy text search on client rules within a specified workflow. Can search on one or two fields
    simultaneously with configurable similarity threshold and result limits.
    
    Args:
        client_workflow_id: Required workflow ObjectId to filter rules
        column1: Optional first field name to search (e.g., "name", "rule_category")
        value1: Optional value to search for in column1
        column2: Optional second field name to search (e.g., "issue_description")
        value2: Optional value to search for in column2
        threshold: Minimum similarity score (0-100), default 80
        top_n: Maximum number of results to return, default 10
        
    Returns:
        APIResponse with matched rules sorted by relevance score
        
    Example:
        /search?column1=name&value1=invoice&column2=rule_category&value2=validation&client_workflow_id=507f1f77bcf86cd799439011&threshold=80&top_n=10
    """
    return await service.search_rules(
        column1=column1,
        value1=value1,
        column2=column2,
        value2=value2,
        client_workflow_id=client_workflow_id,
        threshold=threshold,
        top_n=top_n
    )


# ─────────────────────────────
# GET RULE BY ID
# ─────────────────────────────
@router.get(
    "/{rule_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Get rule by ID",
    description="Retrieves details of a specific client rule using its MongoDB ObjectId."
)
async def get_rule_by_id(
    rule_id: str,
    service: ClientRulesService = Depends(get_client_rules_service)
):
    """Get a client rule by ID"""
    return await service.get_rule_by_id(rule_id)


# ─────────────────────────────
# UPDATE RULE
# ─────────────────────────────
@router.put(
    "/{rule_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a client rule",
    description="Modifies an existing client rule identified by its ObjectId."
)
async def update_rule(
    rule_id: str,
    rule_data: ClientRuleUpdate,
    service: ClientRulesService = Depends(get_client_rules_service)
):
    """Update a client rule"""
    return await service.update_rule(rule_id, rule_data)


# ─────────────────────────────
# DELETE RULE
# ─────────────────────────────
@router.delete(
    "/{rule_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a client rule",
    description="Deletes a rule permanently by ID."
)
async def delete_rule(
    rule_id: str,
    service: ClientRulesService = Depends(get_client_rules_service)
):
    """Delete a client rule"""
    return await service.delete_rule(rule_id)
