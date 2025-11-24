from typing import List, Optional
from datetime import datetime, timezone
from beanie import PydanticObjectId
from bson import ObjectId
from fastapi import HTTPException
from rapidfuzz import fuzz
import logging

from client_service.schemas.mongo_schemas.client_workflow_execution import ClientRules, ClientWorkflows
from client_service.schemas.mongo_schemas.client_workflow_execution import get_searchable_string_fields
from client_service.schemas.pydantic_schemas import (
    ClientRuleCreate,
    ClientRuleUpdate,
    ClientRuleResponse
)
from client_service.schemas.base_response import APIResponse
from client_service.api.constants.status_codes import StatusCode
from client_service.api.constants.messages import ClientRuleMessages

# Initialize logger
logger = logging.getLogger(__name__)


class ClientRulesService:
    """Service class for managing client rules with uniform API responses"""

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

    @staticmethod
    async def create_rule(data: ClientRuleCreate) -> APIResponse:
        """Create a new client rule"""
        logger.info("Creating a new client rule with data: %s", data.dict())
        try:
            # Validate client_workflow_id
            workflow_id = data.client_workflow_id
            if not PydanticObjectId.is_valid(workflow_id):
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST,
                    detail=f"Invalid client_workflow_id: {workflow_id}. Must be a valid ObjectId."
                )

            # Check if the workflow exists
            workflow = await ClientWorkflows.get(PydanticObjectId(workflow_id))
            if not workflow:
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=f"Client workflow with ID {workflow_id} not found."
                )

            # Create the rule with agent_id conversion
            rule_data = data.dict()
            if rule_data.get("relevant_agent"):
                rule_data["relevant_agent"] = ClientRulesService._convert_agent_id_to_objectid(rule_data["relevant_agent"])
            
            rule = ClientRules(**rule_data)
            await rule.insert()
            logger.info("Client rule created successfully: %s", rule.name)
            return APIResponse(
                success=True,
                message=ClientRuleMessages.CREATED_SUCCESS.format(name=rule.name),
                data=[ClientRuleResponse(
                    **{
                        **rule.dict(),
                        "_id": str(rule.id),
                        "client_workflow_id": str(rule.client_workflow_id),
                        "created_at": rule.created_at,
                        "updated_at": rule.updated_at,
                    }
                )],
            )
        except HTTPException as e:
            logger.error("Error creating client rule: %s", e.detail)
            raise e
        except Exception as e:
            logger.error("Error creating client rule: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=ClientRuleMessages.CREATE_ERROR.format(error=str(e))
            )

    # ─────────────────────────────
    # READ: Get by ID
    # ─────────────────────────────
    @staticmethod
    async def get_rule_by_id(rule_id: str) -> APIResponse:
        """Retrieve a single client rule by ID"""
        logger.info("Retrieving client rule with ID: %s", rule_id)
        try:
            rule = await ClientRules.get(PydanticObjectId(rule_id))
            if not rule:
                logger.warning("Client rule not found with ID: %s", rule_id)
                return APIResponse(
                    success=False,
                    message=ClientRuleMessages.NOT_FOUND.format(id=rule_id),
                    data=None,
                )
            logger.info("Client rule retrieved successfully: %s", rule.name)
            return APIResponse(
                success=True,
                message=ClientRuleMessages.RETRIEVED_SUCCESS.format(name=rule.name),
                data=[ClientRuleResponse(
                    **{
                        **rule.dict(),
                        "_id": str(rule.id),
                        "client_workflow_id": str(rule.client_workflow_id),
                        "created_at": rule.created_at,
                        "updated_at": rule.updated_at,
                    }
                )],
            )
        except Exception as e:
            logger.error("Error retrieving client rule: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=ClientRuleMessages.RETRIEVE_ERROR.format(error=str(e))
            )

    # ─────────────────────────────
    # READ: Get All
    # ─────────────────────────────
    @staticmethod
    async def get_all_rules(skip: int = 0, limit: int = 50) -> APIResponse:
        """Retrieve all client rules with pagination"""
        logger.info("Retrieving client rules with pagination: skip=%s, limit=%s", skip, limit)
        try:
            # Fetch paginated rules
            rules = await ClientRules.find_all().skip(skip).limit(limit).to_list()

            logger.info("Retrieved %d client rules (paginated)", len(rules))
            normalized = []
            for rule in rules:
                normalized.append(
                    ClientRuleResponse(
                        **{
                            **rule.dict(),
                            "_id": str(rule.id),
                            "client_workflow_id": str(rule.client_workflow_id),
                            "created_at": rule.created_at,
                            "updated_at": rule.updated_at,
                        }
                    ).model_dump()
                )
            return APIResponse(
                success=True,
                message=ClientRuleMessages.RETRIEVED_ALL_SUCCESS.format(count=len(rules)),
                data=normalized,
            )
        except Exception as e:
            logger.error("Error retrieving client rules: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=ClientRuleMessages.RETRIEVE_ALL_ERROR.format(error=str(e))
            )
    
    @staticmethod
    async def search_rules(
        client_workflow_id: str,
        column1: Optional[str] = None,
        value1: Optional[str] = None,
        column2: Optional[str] = None,
        value2: Optional[str] = None,
        threshold: int = 80,
        top_n: int = 10
    ) -> APIResponse:
        """
        Search client rules by one or two columns with fuzzy matching (optional parameters)
        
        Args:
            column1: Optional first field name to search in
            value1: Optional value to search for in column1
            column2: Optional second field name to search in
            value2: Optional value to search for in column2
            client_workflow_id: Required workflow ID to filter results
            threshold: Minimum similarity score (0-100)
            top_n: Maximum number of results to return
            
        Logic:
            - If only column1/value1 provided: Search on column1 only
            - If only column2/value2 provided: Search on column2 only
            - If both provided: Search where BOTH columns meet threshold
            - If neither: Return all rules for the workflow
        """
        logger.info(
            "Searching client rules: %s='%s' AND %s='%s', threshold=%s, workflow_id=%s",
            column1, value1, column2, value2, threshold, client_workflow_id
        )
        
        try:
            # Define allowed searchable fields
            allowed_fields = set(get_searchable_string_fields(ClientRules))

            sample_rule = await ClientRules.find_one()
            if sample_rule:
                rule_dict = sample_rule.model_dump()
                dynamic_fields = set(rule_dict.keys()) - set(ClientRules.model_fields.keys())
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
            
            # Validate client_workflow_id
            if not PydanticObjectId.is_valid(client_workflow_id):
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST,
                    detail=f"Invalid client_workflow_id: {client_workflow_id}"
                )
            
            # Strip values if provided (check for not None to handle "0" correctly)
            if value1 is not None:
                value1 = value1.strip()
            if value2 is not None:
                value2 = value2.strip()
            
            # Build query filter
            query_filter = {"client_workflow_id": PydanticObjectId(client_workflow_id)}
            
            # Get rules filtered by workflow_id
            all_rules = await ClientRules.find(query_filter).to_list()
            
            if not all_rules:
                logger.info(f"No rules found for workflow_id: {client_workflow_id}")
                return APIResponse(
                    success=True,
                    message=ClientRuleMessages.SEARCH_NO_RESULTS,
                    data=[]
                )
            
            matches = []
            
            # Handle different search modes
            for rule in all_rules:
                match_scores = {}
                is_match = True
                
                # Check column1 if provided
                if column1 and value1:
                    rule_value1 = getattr(rule, column1, None)
                    if rule_value1 is not None:
                        # For integer fields, use exact match; for strings, use fuzzy match
                        if isinstance(rule_value1, int):
                            try:
                                # Try to convert search value to int for exact comparison
                                search_int = int(value1)
                                score1 = 100 if rule_value1 == search_int else 0
                            except ValueError:
                                # If value1 is not a valid int, no match
                                score1 = 0
                        else:
                            # String fuzzy matching
                            score1 = fuzz.partial_ratio(
                                value1.lower(), 
                                str(rule_value1).lower()
                            )
                        match_scores["score1"] = score1
                        if score1 < threshold:
                            is_match = False
                    else:
                        is_match = False
                
                # Check column2 if provided
                if column2 and value2:
                    rule_value2 = getattr(rule, column2, None)
                    if rule_value2 is not None:
                        # For integer fields, use exact match; for strings, use fuzzy match
                        if isinstance(rule_value2, int):
                            try:
                                # Try to convert search value to int for exact comparison
                                search_int = int(value2)
                                score2 = 100 if rule_value2 == search_int else 0
                            except ValueError:
                                # If value2 is not a valid int, no match
                                score2 = 0
                        else:
                            # String fuzzy matching
                            score2 = fuzz.partial_ratio(
                                value2.lower(), 
                                str(rule_value2).lower()
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
                        "rule": rule,
                        "scores": match_scores  # Empty scores
                    })
                elif is_match:
                    matches.append({
                        "rule": rule,
                        "scores": match_scores
                    })
                    logger.debug(
                        f"Match found: {rule.name} (scores: {match_scores})"
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
                    f"No rules found matching provided criteria for workflow {client_workflow_id}"
                )
                return APIResponse(
                    success=True,
                    message=ClientRuleMessages.SEARCH_NO_RESULTS,
                    data=[]
                )
            
            # Format response - handle type conversion
            results = []
            for match in top_matches:
                try:
                    rule_dict = match["rule"].dict()
                    
                    # Ensure string fields are strings
                    string_fields = get_searchable_string_fields(ClientRules)
                    
                    for field in string_fields:
                        if field in rule_dict and rule_dict[field] is not None:
                            if not isinstance(rule_dict[field], str):
                                # Convert to string, handle empty lists/other types
                                if isinstance(rule_dict[field], list):
                                    rule_dict[field] = None  # Convert empty list to None
                                else:
                                    rule_dict[field] = str(rule_dict[field])
                    
                    results.append(ClientRuleResponse(**rule_dict).dict())
                except Exception as e:
                    logger.warning(f"Skipping rule {match['rule'].name} due to validation error: {e}")
                    continue
            
            logger.info(
                f"Found {len(results)} match(es) for workflow {client_workflow_id}"
            )
            
            return APIResponse(
                success=True,
                message=ClientRuleMessages.SEARCH_SUCCESS.format(count=len(results)),
                data=results
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error searching client rules: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=ClientRuleMessages.SEARCH_ERROR.format(error=str(e))
            )

    # ─────────────────────────────
    # UPDATE
    # ─────────────────────────────
    @staticmethod
    async def update_rule(rule_id: str, data: ClientRuleUpdate) -> APIResponse:
        """Update a client rule"""
        logger.info("Updating client rule with ID: %s and data: %s", rule_id, data.dict(exclude_unset=True))
        try:
            rule = await ClientRules.get(PydanticObjectId(rule_id))
            if not rule:
                logger.warning("Client rule not found with ID: %s", rule_id)
                return APIResponse(
                    success=False,
                    message=ClientRuleMessages.NOT_FOUND.format(id=rule_id),
                    data=None,
                )

            update_data = data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(rule, field, value)

            rule.updated_at = datetime.now(timezone.utc)
            await rule.save()

            logger.info("Client rule updated successfully: %s", rule.name)
            return APIResponse(
                success=True,
                message=ClientRuleMessages.UPDATED_SUCCESS.format(name=rule.name),
                data=[ClientRuleResponse(
                    **{
                        **rule.dict(),
                        "_id": str(rule.id),
                        "client_workflow_id": str(rule.client_workflow_id),
                        "created_at": rule.created_at,
                        "updated_at": rule.updated_at,
                    }
                )],
            )
        except Exception as e:
            logger.error("Error updating client rule: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=ClientRuleMessages.UPDATE_ERROR.format(error=str(e))
            )

    # ─────────────────────────────
    # DELETE
    # ─────────────────────────────
    @staticmethod
    async def delete_rule(rule_id: str) -> APIResponse:
        """Delete a client rule"""
        logger.info("Deleting client rule with ID: %s", rule_id)
        try:
            rule = await ClientRules.get(PydanticObjectId(rule_id))
            if not rule:
                logger.warning("Client rule not found with ID: %s", rule_id)
                return APIResponse(
                    success=False,
                    message=ClientRuleMessages.NOT_FOUND.format(id=rule_id),
                    data=None,
                )

            await rule.delete()
            logger.info("Client rule deleted successfully with ID: %s", rule_id)
            return APIResponse(
                success=True,
                message=ClientRuleMessages.DELETED_SUCCESS.format(id=rule_id),
                data=None,
            )
        except Exception as e:
            logger.error("Error deleting client rule: %s", str(e))
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=ClientRuleMessages.DELETE_ERROR.format(error=str(e))
            )
