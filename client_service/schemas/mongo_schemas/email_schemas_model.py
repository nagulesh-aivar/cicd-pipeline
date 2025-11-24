#ginthi_agents/client_service/schemas/mongo_schemas/email_schemas_model.py
from beanie import Document
from datetime import datetime
from pydantic import Field
from typing import Optional
class NotificationTemplateModel(Document):
    template_name: str
    channel: str  # email / whatsapp / notification
    subject: Optional[str] = None
    body: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "templates"

    @classmethod
    async def get_by_name(cls, name: str):
        return await cls.find_one({"template_name": name})

    @classmethod
    async def list_all(cls):
        return await cls.find_all().to_list()
