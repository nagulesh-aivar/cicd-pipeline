from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# --- Feedback Base ---
class FeedbackBase(BaseModel):
    """Base schema for feedback entries."""
    execution_id: int = Field(..., description="ID of the workflow execution", example=101)
    client_id: int = Field(..., description="ID of the client organization", example=1)
    rating: int = Field(..., description="Rating given by the client or lead admin (1-5)", example=5)
    comments: Optional[str] = Field(None, description="Optional comments or feedback notes", example="Very satisfied with execution")
    created_by: Optional[str] = Field(None, description="User who created the feedback")
    updated_by: Optional[str] = Field(None, description="User who last updated the feedback")


# --- Create Feedback ---
class FeedbackCreate(FeedbackBase):
    """Schema for creating a new feedback entry."""
    pass

# --- Update Feedback ---
class FeedbackUpdate(BaseModel):
    """Schema for updating an existing feedback entry."""
    rating: Optional[int] = Field(None, description="Updated rating (1-5)", example=4)
    comments: Optional[str] = Field(None, description="Updated comments or notes", example="Updated feedback text")


# --- Feedback Output ---
class FeedbackOut(FeedbackBase):
    """Schema for returning feedback details."""
    feedback_id: int = Field(..., description="Unique identifier of the feedback entry", example=501)
    execution_id: Optional[int] = Field(None, description="ID of the workflow execution", example=101)
    client_id: int = Field(..., description="ID of the client organization", example=1)
    created_at: datetime = Field(..., description="Timestamp when the feedback was created", example="2025-10-13T12:34:56")

    model_config = {"from_attributes": True}
