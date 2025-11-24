from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# -------------------- CLIENTS --------------------
class ClientBase(BaseModel):
    """Base schema for client organization details."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Full name of the client organization",
        examples=["Acme Corporation", "Tech Innovators Pvt Ltd"]
    )
    industry: Optional[str] = Field(
        None,
        max_length=100,
        description="Industry or business domain of the client",
        examples=["Manufacturing", "IT Services", "Retail"]
    )
    website: Optional[str] = Field(
        None,
        description="Official website URL of the client",
        examples=["https://acme.com"]
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Primary contact email for the client",
        examples=["contact@acme.com"]
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="Client’s primary contact number with country code",
        examples=["+14155552671", "+919876543210"]
    )
    created_by: Optional[str] = Field(None, description="User who created the lead admin")
    updated_by: Optional[str] = Field(None, description="User who last updated the lead admin")


class ClientCreate(ClientBase):
    """Schema for creating a new client record."""
    pass

class ClientUpdate(BaseModel):
    """Schema for updating client information."""

    name: Optional[str] = Field(None, description="Updated client name")
    industry: Optional[str] = Field(None, description="Updated industry name")
    website: Optional[str] = Field(None, description="Updated client website")
    email: Optional[EmailStr] = Field(None, description="Updated contact email")
    phone: Optional[str] = Field(None, description="Updated phone number")
    created_by: Optional[str] = Field(None, description="User who created the client")
    updated_by: Optional[str] = Field(None, description="User who last updated the client")




class ClientOut(ClientBase):
    """Schema for returning client data in API responses."""

    client_id: int = Field(..., description="Unique identifier for the client")
    created_at: datetime = Field(..., description="Timestamp when client was created")
    updated_at: datetime = Field(..., description="Timestamp when client was last updated")

    model_config = {"from_attributes": True}


# -------------------- LEAD ADMINS --------------------
class LeadAdminBase(BaseModel):
    """Base schema for client lead administrator details."""

    client_id: int = Field(..., description="Associated client ID for the lead admin")
    name: str = Field(..., max_length=120, description="Full name of the lead admin")
    email: EmailStr = Field(..., description="Email address of the lead admin")
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="Lead admin’s phone number with country code",
        examples=["+1234567890"]
    )
    created_by: Optional[str] = Field(None, description="User who created the lead admin")
    updated_by: Optional[str] = Field(None, description="User who last updated the lead admin")

class LeadAdminCreate(LeadAdminBase):
    """Schema for creating a new lead admin."""
    pass

class LeadAdminUpdate(BaseModel):
    """Schema for updating lead admin details."""

    name: Optional[str] = Field(None, description="Updated name of the lead admin")
    email: Optional[EmailStr] = Field(None, description="Updated email of the lead admin")
    phone: Optional[str] = Field(None, description="Updated phone number")
    created_by: Optional[str] = Field(None, description="User who created the lead admin")
    updated_by: Optional[str] = Field(None, description="User who last updated the lead admin")


class LeadAdminOut(LeadAdminBase):
    """Schema for returning lead admin information."""

    lead_admin_id: int = Field(..., description="Unique ID of the lead admin")
    
    created_at: datetime = Field(..., description="Timestamp when record was created")
    updated_at: datetime = Field(..., description="Timestamp when record was last updated")

    model_config = {"from_attributes": True}


# -------------------- CLIENT API KEYS --------------------
class ClientAPIKeyBase(BaseModel):
    """Base schema for API key details associated with a client."""

    client_id: int = Field(..., description="Client ID to which this API key belongs")
    api_key: str = Field(..., min_length=10, description="Unique API key string")
    is_active: Optional[bool] = Field(
        True,
        description="Status flag indicating if API key is active",
        examples=[True, False]
    )
    access_controls: Optional[str] = Field(
        None,
        description="Optional JSON or comma-separated string of access permissions",
        examples=["invoices:read,grns:write"]
    )
    created_by: Optional[str] = Field(None, description="User who created the cliientAPI key")
    updated_by: Optional[str] = Field(None, description="User who last updated the clientAPI key")



class ClientAPIKeyCreate(ClientAPIKeyBase):
    """Schema for creating a new client API key."""
    pass

class ClientAPIKeyUpdate(BaseModel):
    """Schema for updating API key details."""

    api_key: Optional[str] = Field(None, description="Updated API key string")
    is_active: Optional[bool] = Field(None, description="Activate or deactivate key")
    access_controls: Optional[str] = Field(None, description="Updated access control details")
    created_by: Optional[str] = Field(None, description="User who created the cliientAPI key")
    updated_by: Optional[str] = Field(None, description="User who last updated the clientAPI key")

    
class ClientAPIKeyOut(ClientAPIKeyBase):
    """Schema for returning API key information in API responses."""

    api_key_id: int = Field(..., description="Unique identifier for the API key")
    created_at: datetime = Field(..., description="Timestamp when API key was created")

    model_config = {"from_attributes": True}
