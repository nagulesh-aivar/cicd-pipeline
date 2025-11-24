import os
import requests
import boto3
import pandas as pd
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# AWS Config
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Service Config
SERVICE_NAME = os.getenv("SERVICE_NAME", "client_service_logs")

# API URL
API_URL = "http://127.0.0.1:8005/api/v1/transaction-logs"


def fetch_transaction_logs():
    """Fetch logs from API and normalize into flat table."""
    print("Fetching data from API...")
    response = requests.get(API_URL)

    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")

    raw_data = response.json().get("data", [])

    if not raw_data:
        print("No logs found from API.")
        return pd.DataFrame()

    # FIX: Normalize nested JSON → flat DataFrame
    df = pd.json_normalize(raw_data)

    return df


def upload_to_s3(df: pd.DataFrame):
    """Convert DataFrame to Parquet and upload to S3."""
    print("Preparing S3 upload...")

    today = datetime.now()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    day = today.strftime("%d")
    date_str = today.strftime("%Y-%m-%d")

    s3_key = f"{SERVICE_NAME}/{year}/{month}/{day}/{SERVICE_NAME}_{date_str}.parquet"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    # Convert DataFrame → Parquet
    buffer = BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    # Upload
    s3.upload_fileobj(buffer, S3_BUCKET_NAME, s3_key)

    print(f"Upload Successful → s3://{S3_BUCKET_NAME}/{s3_key}")


def main():
    try:
        df = fetch_transaction_logs()

        if df.empty:
            print("No data to upload.")
            return

        upload_to_s3(df)

    except Exception as e:
        print("Error:", str(e))


if __name__ == "__main__":
    main()
