from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ClientServerBase(BaseModel):
    """Base schema for client servers."""
    client_id: int = Field(..., description="ID of the client", example=1)
    server_name: str = Field(..., description="Name of the server", example="InvoiceServer01")
    server_url: Optional[str] = Field(None, description="Server URL", example="https://server.example.com")
    server_ip: Optional[str] = Field(None, description="Server IP address", example="192.168.1.10")
    server_port: Optional[int] = Field(None, description="Server port", example=8080)
    server_type: Optional[str] = Field(None, description="Type of server", example="PostgreSQL")
    username: Optional[str] = Field(None, description="Username for server authentication", example="admin")
    password: Optional[str] = Field(None, description="Password for server authentication", example="securePass123")
    is_active: Optional[bool] = Field(True, description="Indicates if the server is active")
    created_by: Optional[str] = Field(None, description="User who created the server")
    updated_by: Optional[str] = Field(None, description="User who last updated the server")


class ClientServerCreate(ClientServerBase):
    """Schema for creating a new client server."""
    pass


class ClientServerUpdate(BaseModel):
    """Schema for updating client server details."""
    server_name: Optional[str] = Field(None, description="Updated server name", example="InvoiceServer02")
    server_url: Optional[str] = Field(None, description="Updated server URL", example="https://newserver.example.com")
    server_ip: Optional[str] = Field(None, description="Updated IP address", example="192.168.1.11")
    server_port: Optional[int] = Field(None, description="Updated port", example=5432)
    server_type: Optional[str] = Field(None, description="Updated server type", example="MySQL")
    username: Optional[str] = Field(None, description="Updated username", example="admin")
    password: Optional[str] = Field(None, description="Updated password", example="newPass123")
    is_active: Optional[bool] = Field(None, description="Update active status")


class ClientServerOut(ClientServerBase):
    """Schema for returning client server info."""
    server_id: int = Field(..., description="Unique identifier for the server", example=101)
    created_at: datetime = Field(..., description="Server creation timestamp", example="2025-10-13T12:34:56")
    updated_at: datetime = Field(..., description="Server last updated timestamp", example="2025-10-13T13:45:00")

    model_config = {"from_attributes": True}
