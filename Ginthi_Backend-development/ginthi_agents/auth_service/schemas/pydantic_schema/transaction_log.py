# auth_service/schemas/pydantic_schema/transaction_log.py
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

class TransactionLogBase(BaseModel):
    user: str
    ip: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    headers: Optional[Dict[str, str]] = None
    request_body: Optional[Dict[str, Any]] = None
    response_body: Optional[Dict[str, Any]] = None

class TransactionLogCreate(TransactionLogBase):
    pass

class TransactionLogRead(TransactionLogBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
