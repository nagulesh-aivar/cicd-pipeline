import boto3
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY = os.getenv("SES_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("SES_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

# DynamoDB resource
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)

# SES client
ses_client = boto3.client(
    "ses",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)

sns_client = boto3.client(
    "sns", 
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL")

EUM_SMS_API_URL = os.getenv("EUM_SMS_API_URL")
EUM_SMS_API_KEY = os.getenv("EUM_SMS_API_KEY")
EUM_SMS_SENDER_ID = os.getenv("EUM_SMS_SENDER_ID")

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")