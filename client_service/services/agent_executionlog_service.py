from typing import List, Optional
from datetime import datetime, timezone
from beanie import PydanticObjectId
from bson import ObjectId
from fastapi import HTTPException
from rapidfuzz import fuzz
import logging

from client_service.schemas.mongo_schemas.client_workflow_execution import AgentExecutionLogs
from client_service.schemas.mongo_schemas.client_workflow_execution import get_searchable_string_fields
from client_service.schemas.pydantic_schemas import (
    AgentExecutionLogCreate,
    AgentExecutionLogUpdate,
    AgentExecutionLogResponse
)
from client_service.schemas.base_response import APIResponse
from client_service.api.constants.status_codes import StatusCode
from client_service.api.constants.messages import AgentExecutionLogMessages

logger = logging.getLogger(__name__)

class AgentExecutionService:
    """Service class for managing agent execution logs"""

    @staticmethod
    def _convert_agent_id_to_objectid(agent_id: Optional[str]) -> Optional[ObjectId]:
        """
        Convert agent_id string to ObjectId if it's a valid 24-character hex string.
        Returns the original string if it's not a valid ObjectId format.
        """
        if agent_id is None:
            return None
        
        # If it's already an ObjectId, return it
        if isinstance(agent_id, ObjectId):
            return agent_id
        
        # Try to convert string to ObjectId if it's a valid 24-char hex string
        if isinstance(agent_id, str) and len(agent_id) == 24:
            try:
                return ObjectId(agent_id)
            except Exception:
                # If conversion fails, return the original string
                return agent_id
        
        return agent_id

    # ─────────────────────────────
    # CREATE
    # ─────────────────────────────
    @staticmethod
    async def create_log(data: AgentExecutionLogCreate) -> APIResponse:
        logger.info("Creating agent execution log with data: %s", data.dict())
        try:
            log_data = data.dict()
            # Convert agent_id to ObjectId if it's a valid 24-char hex string
            if log_data.get("agent_id"):
                log_data["agent_id"] = AgentExecutionService._convert_agent_id_to_objectid(log_data["agent_id"])
            
            log = AgentExecutionLogs(**log_data)
            await log.insert()
            logger.info("Agent execution log created successfully: %s", log.id)
            return APIResponse(
                success=True,
                message=AgentExecutionLogMessages.CREATED_SUCCESS.format(name="AgentExecutionLog"),
                data=[AgentExecutionLogResponse(**log.dict())]
            )
        except Exception as e:
            logger.error("Error creating agent execution log: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=AgentExecutionLogMessages.CREATE_ERROR.format(error=str(e))
            )

    # ─────────────────────────────
    # GET BY ID
    # ─────────────────────────────
    @staticmethod
    async def get_log_by_id(log_id: str) -> APIResponse:
        logger.info("Retrieving agent execution log with ID: %s", log_id)
        try:
            log = await AgentExecutionLogs.get(PydanticObjectId(log_id))
            if not log:
                logger.warning("Agent execution log not found with ID: %s", log_id)
                return APIResponse(
                    success=False,
                    message=AgentExecutionLogMessages.NOT_FOUND.format(id=log_id),
                    data=None
                )
            return APIResponse(
                success=True,
                message=AgentExecutionLogMessages.RETRIEVED_SUCCESS.format(name="AgentExecutionLog"),
                data=[AgentExecutionLogResponse(**log.dict())]
            )
        except Exception as e:
            logger.error("Error retrieving agent execution log: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=AgentExecutionLogMessages.RETRIEVE_ERROR.format(error=str(e))
            )

    # ─────────────────────────────
    # GET ALL
    # ─────────────────────────────
    @staticmethod
    async def get_all_logs(skip: int = 0, limit: int = 50) -> APIResponse:
        """Retrieve all agent execution logs with pagination"""
        logger.info("Retrieving all agent execution logs with pagination skip=%s, limit=%s", skip, limit)
        try:
            logs = await AgentExecutionLogs.find_all().skip(skip).limit(limit).to_list()
            logger.info(AgentExecutionLogMessages.RETRIEVED_ALL_SUCCESS.format(count=len(logs)))

            return APIResponse(
                success=True,
                message=AgentExecutionLogMessages.RETRIEVED_ALL_SUCCESS.format(count=len(logs)),
                data=[
                    AgentExecutionLogResponse.model_validate(log).model_dump()
                    for log in logs
                ]
            )
        except Exception as e:
            logger.error("Error retrieving all agent execution logs: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=AgentExecutionLogMessages.RETRIEVE_ALL_ERROR.format(error=str(e))
            )

    @staticmethod
    async def search_logs(
        workflow_id: str,
        column1: Optional[str] = None,
        value1: Optional[str] = None,
        column2: Optional[str] = None,
        value2: Optional[str] = None,
        threshold: int = 80,
        top_n: int = 10
    ) -> APIResponse:
        """
        Search agent execution logs by one or two columns with fuzzy matching (optional parameters)
        
        Args:
            column1: Optional first field name to search in
            value1: Optional value to search for in column1
            column2: Optional second field name to search in
            value2: Optional value to search for in column2
            workflow_id: Required workflow ID to filter results
            threshold: Minimum similarity score (0-100)
            top_n: Maximum number of results to return
            
        Logic:
            - If only column1/value1 provided: Search on column1 only
            - If only column2/value2 provided: Search on column2 only
            - If both provided: Search where BOTH columns meet threshold
            - If neither: Return all logs for the workflow
        """
        logger.info(
            "Searching agent execution logs: %s='%s' AND %s='%s', threshold=%s, workflow_id=%s",
            column1, value1, column2, value2, threshold, workflow_id
        )
        
        try:
            # Define allowed searchable fields
            allowed_fields = set(get_searchable_string_fields(AgentExecutionLogs))

            sample_rule = await AgentExecutionLogs.find_one()
            if sample_rule:
                rule_dict = sample_rule.model_dump()
                dynamic_fields = set(rule_dict.keys()) - set(AgentExecutionLogs.model_fields.keys())
                allowed_fields.update(dynamic_fields)
            logger.debug(f"Dynamically extracted searchable fields: {allowed_fields}")
            
            # Validate columns if provided
            if column1 and column1 not in allowed_fields:
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST,
                    detail=f"Invalid column1: {column1}. Allowed columns: {', '.join(allowed_fields)}"
                )
            
            if column2 and column2 not in allowed_fields:
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST,
                    detail=f"Invalid column2: {column2}. Allowed columns: {', '.join(allowed_fields)}"
                )
            
            # Validate workflow_id (assuming it's a string ID, no ObjectId validation needed)
            if not workflow_id:
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST,
                    detail="workflow_id is required"
                )
            
            # Strip values if provided
            if value1:
                value1 = value1.strip()
            if value2:
                value2 = value2.strip()
            
            # Build query filter
            query_filter = {"workflow_id": workflow_id}
            
            # Get logs filtered by workflow_id
            all_logs = await AgentExecutionLogs.find(query_filter).to_list()
            
            if not all_logs:
                logger.info(f"No logs found for workflow_id: {workflow_id}")
                return APIResponse(
                    success=True,
                    message=AgentExecutionLogMessages.SEARCH_NO_RESULTS,
                    data=[]
                )
            
            matches = []
            
            # Handle different search modes
            for log in all_logs:
                match_scores = {}
                is_match = True
                
                # Check column1 if provided
                if column1 and value1:
                    log_value1 = getattr(log, column1, None)
                    if log_value1:
                        score1 = fuzz.partial_ratio(
                            value1.lower(), 
                            str(log_value1).lower()
                        )
                        match_scores["score1"] = score1
                        if score1 < threshold:
                            is_match = False
                    else:
                        is_match = False
                
                # Check column2 if provided
                if column2 and value2:
                    log_value2 = getattr(log, column2, None)
                    if log_value2:
                        score2 = fuzz.partial_ratio(
                            value2.lower(), 
                            str(log_value2).lower()
                        )
                        match_scores["score2"] = score2
                        if score2 < threshold:
                            is_match = False
                    else:
                        is_match = False
                
                # If no columns provided, it's a match (return all for this workflow)
                if not column1 and not column2:
                    is_match = True
                    matches.append({
                        "log": log,
                        "scores": match_scores  # Empty scores
                    })
                elif is_match:
                    matches.append({
                        "log": log,
                        "scores": match_scores
                    })
                    logger.debug(
                        f"Match found: {log.id} (scores: {match_scores})"
                    )
            
            # Sort by highest score (prefer score1 if both, else score2, else arbitrary)
            if matches:
                def sort_key(x):
                    scores = x["scores"]
                    if "score1" in scores:
                        return scores["score1"]
                    elif "score2" in scores:
                        return scores["score2"]
                    return 100  # Full match for no-search cases
                matches.sort(key=sort_key, reverse=True)
            
            top_matches = matches[:top_n]
            
            if not top_matches:
                logger.info(
                    f"No logs found matching provided criteria for workflow {workflow_id}"
                )
                return APIResponse(
                    success=True,
                    message=AgentExecutionLogMessages.SEARCH_NO_RESULTS,
                    data=[]
                )
            
            # Format response - handle type conversion
            results = []
            for match in top_matches:
                try:
                    log_dict = match["log"].dict()
                    
                    # Ensure string fields are strings (adapt as needed for log fields)
                    string_fields = get_searchable_string_fields(AgentExecutionLogs)
                    
                    for field in string_fields:
                        if field in log_dict and log_dict[field] is not None:
                            if not isinstance(log_dict[field], str):
                                # Convert to string, handle empty lists/other types
                                if isinstance(log_dict[field], list):
                                    log_dict[field] = None  # Convert empty list to None
                                else:
                                    log_dict[field] = str(log_dict[field])
                    
                    results.append(AgentExecutionLogResponse(**log_dict).dict())
                except Exception as e:
                    logger.warning(f"Skipping log {match['log'].id} due to validation error: {e}")
                    continue
            
            logger.info(
                f"Found {len(results)} match(es) for workflow {workflow_id}"
            )
            
            return APIResponse(
                success=True,
                message=AgentExecutionLogMessages.SEARCH_SUCCESS.format(count=len(results)),
                data=results
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error searching agent execution logs: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=AgentExecutionLogMessages.SEARCH_ERROR.format(error=str(e))
            )
    # ─────────────────────────────
    # UPDATE
    # ─────────────────────────────
    @staticmethod
    async def update_log(log_id: str, data: AgentExecutionLogUpdate) -> APIResponse:
        logger.info("Updating agent execution log ID %s with data: %s", log_id, data.dict(exclude_unset=True))
        try:
            log = await AgentExecutionLogs.get(PydanticObjectId(log_id))
            if not log:
                return APIResponse(
                    success=False,
                    message=AgentExecutionLogMessages.NOT_FOUND.format(id=log_id),
                    data=None
                )

            update_data = data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(log, field, value)

            log.updated_at = datetime.now(timezone.utc)
            await log.save()

            return APIResponse(
                success=True,
                message=AgentExecutionLogMessages.UPDATED_SUCCESS.format(name="AgentExecutionLog"),
                data=[AgentExecutionLogResponse(**log.dict())]
            )
        except Exception as e:
            logger.error("Error updating agent execution log: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=AgentExecutionLogMessages.UPDATE_ERROR.format(error=str(e))
            )

    # ─────────────────────────────
    # DELETE
    # ─────────────────────────────
    @staticmethod
    async def delete_log(log_id: str) -> APIResponse:
        logger.info("Deleting agent execution log with ID: %s", log_id)
        try:
            log = await AgentExecutionLogs.get(PydanticObjectId(log_id))
            if not log:
                return APIResponse(
                    success=False,
                    message=AgentExecutionLogMessages.NOT_FOUND.format(id=log_id),
                    data=None
                )

            await log.delete()
            return APIResponse(
                success=True,
                message=AgentExecutionLogMessages.DELETED_SUCCESS.format(id=log_id),
                data=None
            )
        except Exception as e:
            logger.error("Error deleting agent execution log: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=AgentExecutionLogMessages.DELETE_ERROR.format(error=str(e))
            )
