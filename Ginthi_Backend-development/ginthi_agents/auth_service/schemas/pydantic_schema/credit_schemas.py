from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ---------------------- AI Credit Ledger ----------------------
class CreditLedgerBase(BaseModel):
    """Base schema for a client's AI credit ledger."""
    client_id: int = Field(..., description="Unique identifier of the client", example=1)
    current_balance: int = Field(0, description="Current credit balance of the client", example=1000)
    created_by: Optional[str] = Field(None, description="User who created the ledger")
    updated_by: Optional[str] = Field(None, description="User who last updated the ledger")



class CreditLedgerOut(CreditLedgerBase):
    """Schema for credit ledger response."""
    last_updated: datetime = Field(..., description="Timestamp when the ledger was last updated", example="2025-10-13T12:34:56")

    model_config = {"from_attributes": True}


# ---------------------- AI Credit Entries ----------------------
class CreditEntryBase(BaseModel):
    """Base schema for a credit entry."""
    client_id: int = Field(..., description="Unique identifier of the client", example=1)
    execution_id: Optional[int] = Field(None, description="Optional ID of the workflow or execution associated with this credit change", example=123)
    change_amount: int = Field(..., description="Amount of credit added or deducted", example=50)
    reason: Optional[str] = Field(None, description="Reason or note for the credit change", example="Adjustment after workflow execution")
    created_by: Optional[str] = Field(None, description="User who created the credit entry")
    updated_by: Optional[str] = Field(None, description="User who last updated the credit entry")



class CreditEntryCreate(CreditEntryBase):
    """Schema for creating a new credit entry."""
    pass


class CreditEntryUpdate(BaseModel):
    """Schema for updating an existing credit entry."""
    change_amount: Optional[int] = Field(None, description="Updated credit amount", example=75)
    reason: Optional[str] = Field(None, description="Updated reason for the credit change", example="Manual adjustment")


class CreditEntryOut(CreditEntryBase):
    """Schema for credit entry response."""
    credit_entry_id: int = Field(..., description="Unique identifier for the credit entry", example=1)
    created_at: datetime = Field(..., description="Timestamp when the credit entry was created", example="2025-10-13T12:34:56")

    model_config = {"from_attributes": True}
