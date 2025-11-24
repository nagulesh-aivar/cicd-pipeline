from pydantic import BaseModel
from typing import Any, Optional

class StandardResponse(BaseModel):
    status: bool              
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
