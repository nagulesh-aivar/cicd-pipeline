import os
import json
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

# -------------------------------------------------
# Load environment variables
# -------------------------------------------------
load_dotenv()

# AWS Configuration
AWS_ACCESS_KEY = os.getenv("S3_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("S3_BUCKET_REGION")

BUCKET_NAME = "ginth-etl"
PREFIX = "supply_note/vendor_data/source/"
PROCESSED_PREFIX = "supply_note/vendor_data/processed/"

# -------------------------------------------------
# Step 1: Validate AWS Credentials and Connection
# -------------------------------------------------
print("🔐 Validating AWS credentials...")

try:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
    )
    # Test connection
    s3.list_buckets()
    print("✅ AWS S3 connection successful.")
except NoCredentialsError:
    raise Exception("❌ AWS credentials not found. Please set them as environment variables.")
except ClientError as e:
    raise Exception(f"❌ AWS Client Error: {e}")

# -------------------------------------------------
# Step 2: Fetch CSV Files from S3
# -------------------------------------------------
print("\n🔍 Searching for vendor CSV files in S3...")

try:
    objects = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)
except ClientError as e:
    raise Exception(f"❌ Error listing S3 objects: {e}")

if not objects.get("Contents"):
    print(f"⚠️ No files found under s3://{BUCKET_NAME}/{PREFIX}")
    exit(0)

# Sort by modified date (newest first) and filter only CSV files
sorted_objects = sorted(objects["Contents"], key=lambda obj: obj["LastModified"], reverse=True)
csv_keys = [obj["Key"] for obj in sorted_objects if obj["Key"].endswith(".csv")]

if not csv_keys:
    raise FileNotFoundError(f"No CSV files found under s3://{BUCKET_NAME}/{PREFIX}")

print(f"✅ Found {len(csv_keys)} CSV file(s). Combining...")

# -------------------------------------------------
# Step 3: Combine and Clean CSV Data
# -------------------------------------------------
all_data = []

for key in csv_keys:
    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        csv_str = obj["Body"].read().decode("utf-8")

        # Skip invalid or empty files
        if "NO DATA FOUND FOR THIS QUERY" in csv_str or not csv_str.strip():
            print(f"⚠️ Skipping invalid or empty file: {key}")
            continue

        df = pd.read_csv(StringIO(csv_str))

         # Ensure data_version exists and is numeric
        if "data_version" not in df.columns:
            df["data_version"] = datetime.now().timestamp()  # unique per file
            print(f"🕒 Added 'data_version' to file: {key}")

        else:
            # Coerce invalid values to numeric timestamps
            df["data_version"] = pd.to_numeric(df["data_version"], errors="coerce")
            missing_mask = df["data_version"].isna()
            if missing_mask.any():
                df.loc[missing_mask, "data_version"] = datetime.now().timestamp()
                print(f"🕒 Filled missing 'data_version' values in file: {key}")
        all_data.append(df)

    except Exception as e:
        print(f"❌ Error reading {key}: {e}")

if not all_data:
    raise ValueError("❌ No valid CSV data found in S3 files.")

# Combine all CSVs into a single DataFrame
combined_df = pd.concat(all_data, ignore_index=True)
print(f"📊 Combined shape before cleaning: {combined_df.shape}")

# -------------------------------------------------
# Step 4: Data Cleaning and Deduplication
# -------------------------------------------------

# Validate 'Vendor Code' existence
if "Vendor Code" not in combined_df.columns:
    raise Exception("❌ 'Vendor Code' column missing in CSVs!")

combined_df["data_version"] = (
    pd.to_numeric(combined_df["data_version"], errors="coerce")
    .fillna(0)
    .astype(int)
)

# Rank and keep latest data_version per Vendor Code
combined_df["rank"] = (
    combined_df.groupby("Vendor Code")["data_version"]
    .rank(method="first", ascending=False)
)

clean_df = (
    combined_df[combined_df["rank"] == 1]
    .drop(columns=["rank"])
    .reset_index(drop=True)
)

print(f"✅ After deduplication: {clean_df.shape}")
print(f"📋 Columns: {clean_df.columns.tolist()}")

# -------------------------------------------------
# Step 5: Transform Data → VendorMaster Schema
# -------------------------------------------------
vendor_records = []

for _, row in clean_df.iterrows():
    record = {
        "vendor_code": str(row.get("Vendor Code") or "").strip() or None,
        "vendor_name": str(row.get("Supplier Name") or "").strip() or None,
        "email": str(row.get("Email") or "").strip() or None,
        "gst_id": str(row.get("GST") or "").strip() or None,
        "company_pan": str(row.get("PAN") or "").strip() or None,
        "bank_acc_no": str(row.get("Account Number") or "").strip() or None,
        "beneficiary_name": str(row.get("Beneficiary") or "").strip() or None,
        "ifsc_code": str(row.get("IFSC") or "").strip() or None,
        "payment_term_days": (
            int(row.get("Approved Credit Period"))
            if pd.notna(row.get("Approved Credit Period"))
            and str(row.get("Approved Credit Period")).isdigit()
            else None
        ),
        "user_phone": str(row.get("Phone") or "").strip() or None,
    }

    if record["vendor_code"] or record["vendor_name"]:
        vendor_records.append(record)

# -------------------------------------------------
# Step 6: Save Output JSON
# -------------------------------------------------
final_json = {"data": vendor_records}
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_filename = f"vendor_master_output_{timestamp}.json"

with open(output_filename, "w", encoding="utf-8") as f:
    json.dump(final_json, f, indent=2, ensure_ascii=False)

print(f"\n✅ JSON file saved: {output_filename}")
print(f"✅ Total vendor records: {len(vendor_records)}")

# Step 7: Move Processed CSVs to Processed Folder
# -------------------------------------------------
print("\n📦 Moving processed CSVs to processed folder in S3...")

moved_count = 0

for source_key in csv_keys:
    try:
        filename = source_key.split('/')[-1]
        destination_key = f"{PROCESSED_PREFIX}{filename}"

        # Copy file to processed folder
        s3.copy_object(
            CopySource={'Bucket': BUCKET_NAME, 'Key': source_key},
            Bucket=BUCKET_NAME,
            Key=destination_key
        )

        # Delete file from source folder
        s3.delete_object(Bucket=BUCKET_NAME, Key=source_key)
        moved_count += 1
        print(f"✅ Moved: {filename}")

    except Exception as e:
        print(f"❌ Failed to move {filename}: {str(e)}")

print(f"\n{'='*60}")
print(f"✅ Successfully moved {moved_count}/{len(csv_keys)} files")
print(f"📁 Location: s3://{BUCKET_NAME}/{PROCESSED_PREFIX}")
print(f"{'='*60}\n")
