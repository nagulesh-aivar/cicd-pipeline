# client_service/services/notification_service.py
import json
import logging
import requests
from fastapi import HTTPException
from botocore.exceptions import ClientError

from client_service.config import (
    ses_client,
    EUM_SMS_API_KEY,
    EUM_SMS_SENDER_ID,
    EUM_SMS_API_URL,
    WHATSAPP_API_URL,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    SES_SENDER_EMAIL,
)
from client_service.schemas.mongo_schemas.email_schemas_model import NotificationTemplateModel
from client_service.schemas.pydantic_schemas import (
    SendNotificationRequest,
    SendNotificationResponse,
    TemplateResponse,
)
from client_service.schemas.base_response import APIResponse
from client_service.api.constants.messages import NotificationMessages
from client_service.api.constants.status_codes import StatusCode
from client_service.utils.pydantic_utils import map_to_pydantic

logger = logging.getLogger(__name__)


class NotificationService:

    async def list_templates(self) -> APIResponse:
        templates = await NotificationTemplateModel.list_all()
        response_data = [map_to_pydantic(TemplateResponse, t.dict()) for t in templates]
        logger.info(NotificationMessages.TEMPLATE_LIST_SUCCESS.format(count=len(response_data)))
        return APIResponse(
            success=True,
            message=NotificationMessages.TEMPLATE_LIST_SUCCESS.format(count=len(response_data)),
            data=response_data
        )

    async def get_template(self, name: str) -> APIResponse:
        template = await NotificationTemplateModel.get_by_name(name)
        if not template:
            logger.warning(NotificationMessages.TEMPLATE_NOT_FOUND.format(name=name))
            raise HTTPException(
                status_code=StatusCode.NOT_FOUND,
                detail=NotificationMessages.TEMPLATE_NOT_FOUND.format(name=name)
            )
        logger.info(NotificationMessages.TEMPLATE_RETRIEVED_SUCCESS.format(name=name))
        return APIResponse(
            success=True,
            message=NotificationMessages.TEMPLATE_RETRIEVED_SUCCESS.format(name=name),
            data=[map_to_pydantic(TemplateResponse, template.dict())]
        
        )
    async def send_notification(self, request: SendNotificationRequest) -> APIResponse:
        template = await NotificationTemplateModel.get_by_name(request.template_name)
        if not template:
            logger.warning(NotificationMessages.TEMPLATE_NOT_FOUND.format(name=request.template_name))
            raise HTTPException(
                status_code=StatusCode.NOT_FOUND,
                detail=NotificationMessages.TEMPLATE_NOT_FOUND.format(name=request.template_name)
            )

        # Replace variables
        try:
            body = template.body
            subject = template.subject or ""
            for k, v in (request.variables or {}).items():
                body = body.replace(f"{{{{{k}}}}}", str(v))
                subject = subject.replace(f"{{{{{k}}}}}", str(v))
        except Exception as e:
            logger.error(NotificationMessages.TEMPLATE_VARIABLE_ERROR)
            raise HTTPException(
                status_code=400,
                detail=NotificationMessages.TEMPLATE_VARIABLE_ERROR
            )

        # Select channel
        if request.channel == "email":
            message_id = self._send_email(request.recipient, subject, body)

        elif request.channel == "sms":
            message_id = self._send_sms(request.recipient, body)

        elif request.channel == "whatsapp":
            message_id = self._send_whatsapp(request.recipient, body)

        elif request.channel == "notification":
            message_id = "push_notification_mock"

        else:
            logger.error(NotificationMessages.INVALID_CHANNEL)
            raise HTTPException(
                status_code=StatusCode.BAD_REQUEST,
                detail=NotificationMessages.INVALID_CHANNEL
            )

        logger.info(NotificationMessages.NOTIFICATION_SENT_SUCCESS.format(channel=request.channel))

        return APIResponse(
            success=True,
            message=NotificationMessages.NOTIFICATION_SENT_SUCCESS.format(channel=request.channel),
            data=[{"message": "Sent", "message_id": message_id}]
        )
    
    # ---------- Internal senders ----------
    def _send_email(self, to_email: str, subject: str, body: str):
        try:
            response = ses_client.send_email(
                Source=SES_SENDER_EMAIL,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Html": {"Data": body}, "Text": {"Data": body}}
                },
            )
            return response.get("MessageId")
        except ClientError as e:
            logger.error(NotificationMessages.EMAIL_SEND_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=400,
                detail=NotificationMessages.EMAIL_SEND_ERROR.format(error=str(e))
            )

    def _send_sms(self, phone_number: str, body: str):
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {EUM_SMS_API_KEY}"
            }

            payload = {
                "sender_id": EUM_SMS_SENDER_ID,
                "to": phone_number,
                "message": body,
                "type": "text"
            }

            response = requests.post(EUM_SMS_API_URL, json=payload, headers=headers)
            data = response.json()

            if response.status_code >= 400:
                logger.error(NotificationMessages.SMS_API_ERROR.format(error=data))
                raise HTTPException(
                    status_code=400,
                    detail=NotificationMessages.SMS_API_ERROR.format(error=data)
                )

            return data.get("message_id", "eum_sms_sent")

        except Exception as e:
            logger.error(NotificationMessages.SMS_SEND_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=500,
                detail=NotificationMessages.SMS_SEND_ERROR.format(error=str(e))
            )

    def _send_whatsapp(self, phone_number: str, body: str):
        try:
            url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": body}
            }
            headers = {
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, json=payload)
            data = response.json()

            if response.status_code >= 400:
                logger.error(NotificationMessages.WHATSAPP_API_ERROR.format(error=data))
                raise HTTPException(
                    status_code=400,
                    detail=NotificationMessages.WHATSAPP_API_ERROR.format(error=data)
                )

            return data.get("messages", [{}])[0].get("id")

        except Exception as e:
            logger.error(NotificationMessages.WHATSAPP_SEND_ERROR.format(error=str(e)))
            raise HTTPException(
                status_code=500,
                detail=NotificationMessages.WHATSAPP_SEND_ERROR.format(error=str(e))
            )
