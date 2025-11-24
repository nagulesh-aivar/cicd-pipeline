# client_service/api/routes/notification_router.py
from fastapi import APIRouter, HTTPException, status
from client_service.services.email_service import NotificationService
from client_service.schemas.pydantic_schemas import SendNotificationRequest, TemplateCreateRequest, TemplateUpdateRequest
from client_service.schemas.base_response import APIResponse

router = APIRouter()
service = NotificationService()

# List templates
@router.get("/templates/", status_code=status.HTTP_200_OK)
async def list_templates():
    return (await service.list_templates()).dict()

# Get template
@router.get("/templates/{template_name}", status_code=status.HTTP_200_OK)
async def get_template(template_name: str):
    return (await service.get_template(template_name)).dict()

# Send notification
@router.post("/send/", status_code=status.HTTP_200_OK)
async def send_notification(req: SendNotificationRequest):
    return (await service.send_notification(req)).dict()

# --- Admin endpoints you can add (optional) ---
# Note: create / update / delete endpoints can be added later using NotificationTemplateModel directly
