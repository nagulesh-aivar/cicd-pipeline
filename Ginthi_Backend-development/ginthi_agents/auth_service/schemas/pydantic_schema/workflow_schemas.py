from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ---------------------- Workflows ----------------------
class WorkflowBase(BaseModel):
    """Base schema for a workflow."""
    name: str = Field(..., description="Name of the workflow", example="Invoice Approval Workflow")
    description: Optional[str] = Field(None, description="Detailed description of the workflow", example="Handles client invoice approvals.")
    created_by: Optional[str] = Field(None, description="User who created the workflow")
    updated_by: Optional[str] = Field(None, description="User who last updated the workflow")


class WorkflowCreate(WorkflowBase):
    """Schema for creating a new workflow."""
    pass


class WorkflowUpdate(BaseModel):
    """Schema for updating workflow details."""
    name: Optional[str] = Field(None, description="Updated workflow name", example="Invoice Approval Workflow v2")
    description: Optional[str] = Field(None, description="Updated description", example="Updated workflow for handling invoices.")



class WorkflowOut(WorkflowBase):
    """Schema for workflow response."""
    workflow_id: int = Field(..., description="Unique identifier for the workflow", example=1)
    created_at: datetime = Field(..., description="Timestamp when workflow was created", example="2025-10-13T12:34:56")
    updated_at: datetime = Field(..., description="Timestamp when workflow was last updated", example="2025-10-13T13:45:00")

    model_config = {"from_attributes": True}


# ---------------------- Workflow Executions ----------------------
class WorkflowExecutionBase(BaseModel):
    """Base schema for workflow execution."""
    client_id: int = Field(..., description="Unique identifier of the client", example=1)
    workflow_id: int = Field(..., description="ID of the workflow being executed", example=1)
    lead_admin_id: Optional[int] = Field(None, description="ID of the lead admin triggering the execution", example=2)
    api_key_id: Optional[int] = Field(None, description="API key used for execution if applicable", example=5)
    status: Optional[str] = Field(None, description="Current status of the execution", example="completed")
    duration_seconds: Optional[int] = Field(None, description="Execution duration in seconds", example=120)
    created_by: Optional[str] = Field(None, description="User who created the execution")
    updated_by: Optional[str] = Field(None, description="User who last updated the execution")



class WorkflowExecutionCreate(WorkflowExecutionBase):
    """Schema for creating a workflow execution."""
    pass


class WorkflowExecutionUpdate(BaseModel):
    """Schema for updating workflow execution."""
    status: Optional[str] = Field(None, description="Updated status", example="failed")
    duration_seconds: Optional[int] = Field(None, description="Updated execution duration in seconds", example=130)



class WorkflowExecutionOut(WorkflowExecutionBase):
    """Schema for workflow execution response."""
    execution_id: int = Field(..., description="Unique identifier for the execution", example=101)
    execution_timestamp: datetime = Field(..., description="Timestamp when execution was started", example="2025-10-13T12:45:00")

    model_config = {"from_attributes": True}