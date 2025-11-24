from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Any, Dict, Union, get_origin, get_args

from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CLIENT_WORKFLOWS
# ─────────────────────────────────────────────

class DocumentLink(BaseModel):
    """Represents a link from this document to another document"""
    target_model: str = Field(..., description="Target document model name (e.g., 'invoice', 'purchase_order')")
    source_field: str = Field(..., description="Field in this document that contains the reference")
    target_field: str = Field(..., description="Field in target document that matches the reference")
    fuzzy: Optional[bool] = Field(default=False, description="Whether to use fuzzy matching for this link")
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_model": "invoice",
                "source_field": "invoice_id",
                "target_field": "invoice_number",
                "fuzzy": True
            }
        }


class LinkedDocumentModel(BaseModel):
    """Document model that links to the primary or other documents"""
    model: str = Field(..., description="Document model name (e.g., 'purchase_order', 'grn')")
    is_mandatory: bool = Field(default=False, description="Whether this document is required in the workflow")
    links_to: List[DocumentLink] = Field(
        ..., 
        description="List of links from this document to other documents (primary or other linked documents)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "grn",
                "is_mandatory": False,
                "links_to": [
                    {
                        "target_model": "purchase_order",
                        "source_field": "purchase_id",
                        "target_field": "purchase_order_id"
                    },
                    {
                        "target_model": "invoice",
                        "source_field": "invoice_id",
                        "target_field": "invoice_number"
                    }
                ]
            }
        }


class RelatedDocumentModelWithLinks(BaseModel):
    """Complete document relationship structure with primary model and linked documents"""
    primary_model: str = Field(..., description="Primary document model (e.g., 'invoice')")
    linked_models: List[LinkedDocumentModel] = Field(
        default_factory=list,
        description="Other document models that link to primary or each other"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "primary_model": "invoice",
                "linked_models": [
                    {
                        "model": "purchase_order",
                        "is_mandatory": True,
                        "links_to": [
                            {
                                "target_model": "invoice",
                                "source_field": "purchase_order_id",
                                "target_field": "purchase_order_id"
                            }
                        ]
                    },
                    {
                        "model": "grn",
                        "is_mandatory": False,
                        "links_to": [
                            {
                                "target_model": "purchase_order",
                                "source_field": "purchase_id",
                                "target_field": "purchase_order_id"
                            },
                            {
                                "target_model": "invoice",
                                "source_field": "invoice_id",
                                "target_field": "invoice_number"
                            }
                        ]
                    }
                ]
            }
        }


class ClientWorkflows(Document):

    name: str = Field(..., description="Name of the client workflow")
    central_workflow_id: Optional[str] = Field(None, description="Reference to central workflow ID")
    central_module_id: Optional[str] = Field(None, description="Reference to central module ID")
    description: Optional[str] = Field(None, description="Workflow description")
    expense_categories: Optional[List[str]] = Field(default_factory=list, description="List of expense categories")
    expense_filter: Optional[Dict[str, Any]] = Field(None, description="Expense filter conditions")
    agent_flow_definition: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Definition of agent flow")
    related_document_models: Optional[List[Union[str, RelatedDocumentModelWithLinks]]] = Field(
        default_factory=list, 
        description="Related document models - can be simple strings or objects with relationship links (backward compatible)"
    )

    created_by: Optional[str] = Field(None, description="User who created the workflow")
    updated_by: Optional[str] = Field(None, description="User who last updated the workflow")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('related_document_models', mode='before')
    @classmethod
    def normalize_related_document_models(cls, v):
        """Convert single dict to list for backward compatibility"""
        if v is None:
            return []
        if isinstance(v, dict):
            # If it's a single dict with primary_model, wrap it in a list
            return [v]
        if isinstance(v, list):
            return v
        return []

    class Settings:
        name = "client_workflows"  # Collection name for client workflows


# ─────────────────────────────────────────────
# CLIENT_RULES
# ─────────────────────────────────────────────

class ClientRules(Document):

    client_workflow_id: PydanticObjectId = Field(..., description="ClientWorkflows ObjectId")
    name: str = Field(..., description="Rule name")
    rule_category: Optional[str] = Field(None, description="Category of the rule")
    relevant_agent: Optional[Union[str, PydanticObjectId]] = Field(None, description="Relevant agent ID (ObjectId or string for backward compatibility)")
    prompt: Optional[str] = Field(None, description="Prompt for the rule logic")
    issue_description: Optional[str] = Field(None, description="Detailed description of the issue")
    issue_priority: Optional[int] = Field(None, description="Priority of the issue")
    suggested_resolution: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Suggested resolution objects")
    breach_level: Optional[str] = Field(None, description="Severity or breach level")
    additional_tools: Optional[List[str]] = Field(default_factory=list, description="Additional tools for rule execution")
    ping_target: Optional[List[str]] = Field(default_factory=list, description="Targets to notify/ping")
    related_document_models: Optional[List[str]] = Field(default_factory=list, description="List of related document models")

    resolution_format: Optional[str] = Field(None, description="Expected output or resolution format")
    created_by: Optional[str] = Field(None, description="User who created the rule")
    updated_by: Optional[str] = Field(None, description="User who last updated the rule")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "client_rules"  # Collection name for client rules


# ─────────────────────────────────────────────
# WORKFLOW_EXECUTION_LOGS
# ─────────────────────────────────────────────

class WorkflowContext(BaseModel):
    triggered_by: str = Field(..., description="User or system that triggered the workflow")

class WorkflowExecutionLogs(Document):

    client_workflow_id: PydanticObjectId = Field(..., description="Associated client workflow ID")
    input_files: List[str] = Field(..., description="Input files or document references")
    status: Optional[str] = Field(None, description="Workflow execution status (pending, in_progress, completed, failed)")
    source_trigger: Optional[str] = Field(None, description="Source that triggered the workflow")
    context: Optional[WorkflowContext] = Field(None, description="Contextual data for execution")
    central_workflow_id: Optional[str] = Field(None, description="Reference to central workflow ID")
    created_by: Optional[str] = Field(None, description="User who initiated the execution")
    updated_by: Optional[str] = Field(None, description="User who last updated the execution log")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workflow_execution_logs"  # Collection name for workflow execution logs


# ─────────────────────────────────────────────
# AGENT_EXECUTION_LOGS
# ─────────────────────────────────────────────

class RelatedDocumentModel(BaseModel):
    model: str = Field(..., alias="model_type")
    id: str = Field(..., alias="model_id")
    
    class Config:
        populate_by_name = True


class ProcessLogStep(BaseModel):
    step: str
    status: str


class RuleExecutionOutput(BaseModel):
    """Output structure for individual rule execution in agent logs"""
    client_rule_id: str = Field(..., description="Reference to the client rule ObjectId (24-char hex string)")
    passed: bool = Field(..., description="Whether the rule validation passed")
    user_output: Optional[str] = Field(None, description="Human-readable output for this rule")
    suggested_resolution: Optional[str] = Field(None, description="Suggested resolution if rule failed")
    breach_level: Optional[Union[str, int]] = Field(None, description="Severity level of breach (low, medium, high, critical) or priority number")
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_rule_id": "673a1b2c3d4e5f6a7b8c9d0e",
                "passed": False,
                "user_output": "Invoice amount exceeds threshold",
                "suggested_resolution": "Require manager approval",
                "breach_level": "medium"
            }
        }


class AgentExecutionLogs(Document):

    model_config = ConfigDict(extra="allow")

    workflow_execution_log_id: Link[WorkflowExecutionLogs]
    workflow_id: Optional[str] = Field(None, description="Workflow ID reference")
    agent_id: Optional[Union[str, PydanticObjectId]] = Field(..., description="Agent unique identifier (ObjectId or string for backward compatibility)")
    status: Optional[str] = Field(None, description="Execution status (success, failed, pending, etc.)")
    user_output: Optional[str] = Field(None, description="Readable output message for users")
    error_output: Optional[str] = Field(None, description="Error details if execution failed")
    process_log: Optional[List[ProcessLogStep]] = Field(default_factory=list, description="Step-by-step execution log")
    related_document_models: Optional[List[Union[str, RelatedDocumentModel]]] = Field(
        default_factory=list,
        description="List of related document models (backward-compatible: strings or objects)",
    )

    rule_wise_output: Optional[List[RuleExecutionOutput]] = Field(default_factory=list, description="Array of rule-level execution results")
    breach_status: Optional[str] = Field(None, description="Overall breach status based on rule validations (e.g., 'no_breach', 'low', 'medium', 'high', 'critical')")
    user_feedback: Optional[str] = Field(None, description="Feedback provided by the user on the output", example="Looks good")
    suggested_resolution: Optional[Any] = Field(None, description="Recommended next action or resolution", example="No action required")
    quick_response_actions: Optional[List[str]] = Field(default_factory=list, description="List of quick response actions suggested by the system", example=["notify_user"])
    resolution_format: Optional[str] = Field(None, description="Format of the resolution", example="text")
    created_by: Optional[str] = Field(None, description="User who created the log")
    updated_by: Optional[str] = Field(None, description="User who last updated the log")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "agent_execution_logs"  # Collection name for agent execution logs


def get_searchable_string_fields(model_class) -> List[str]:
    """
    Dynamically extract searchable field names from a Pydantic/Beanie model.
    Includes: string fields and integer fields (for exact matching)
    Excludes: id, timestamps, Link fields, List fields, Dict fields
    """
    searchable_fields = []
    
    # Generic excludes that work across models; can be extended if needed
    exclude_fields = {
        "id", "_id", "revision_id", 
        "created_at", "updated_at",  # Timestamps
        "client_workflow_id", "workflow_execution_log_id",  # Link fields (add more as needed)
    }
    
    for field_name, field_info in model_class.model_fields.items():
        if field_name in exclude_fields:
            continue
        
        annotation = field_info.annotation
        origin = get_origin(annotation)
        
        # Handle Optional[X] (Union[X, None])
        if origin is Union:
            args = get_args(annotation)
            non_none_types = [arg for arg in args if arg is not type(None)]
            for arg_type in non_none_types:
                # Include str, int, and Any types
                if arg_type is str or arg_type is int or arg_type is Any or str(arg_type) == 'typing.Any':
                    searchable_fields.append(field_name)
                    break
        elif annotation is str or annotation is int or annotation is Any or str(annotation) == 'typing.Any':
            searchable_fields.append(field_name)
    
    return searchable_fields