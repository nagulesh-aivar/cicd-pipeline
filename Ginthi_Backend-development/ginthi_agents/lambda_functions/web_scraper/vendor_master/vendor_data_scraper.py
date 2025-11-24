import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import boto3
import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# ---------- Core scraper (reusable) ----------
def scrape_vendor_data(
    email,
    password,
    headless=True,
    base_url="https://supplynote.in",
    upload_to_s3=True,
    s3_bucket=None,
    is_lambda=False,
):
    """
    Core Playwright logic for vendor data scraping.
    Reusable by both Lambda and local entrypoints.
    """
    # Determine if running in Lambda environment
    if is_lambda or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        # Full launch args for Lambda/containerized environments
        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--no-zygote",
            "--single-process",
            "--disable-gpu",
            "--disable-gpu-sandbox",
            "--disable-gpu-compositing",
            "--disable-accelerated-2d-canvas",
            "--disable-accelerated-video-decode",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
            "--use-gl=swiftshader",
            "--use-angle=swiftshader",
            "--disable-web-security",
            "--ignore-certificate-errors",
            "--window-size=1280,800",
            "--hide-scrollbars",
            "--mute-audio",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-client-side-phishing-detection",
            "--renderer-process-limit=1",
            "--no-startup-window",
            "--no-first-run",
            "--disable-default-apps",
            "--no-service-autorun",
            "--password-store=basic",
        ]
    else:
        # Minimal args for local development (Windows/Mac/Linux)
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]

    with sync_playwright() as p:
        print(f"🧠 Launching Chromium (headless={headless}) for vendor scraping...")
        browser = None
        local_file_path = None

        try:
            # Launch browser with appropriate settings
            print(f"🔧 Launch args: {len(launch_args)} arguments configured")
            browser = p.chromium.launch(
                headless=headless,
                args=launch_args,
                timeout=120000,
                slow_mo=100 if not headless else 0,  # Slow down actions in headed mode for visibility
            )
            
            # Create context with download support
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Set default timeout
            page.set_default_timeout(60000)
            print("✅ Browser launched successfully")

            # Step 1: Login
            login_url = f"{base_url}/signin"
            page.goto(login_url, timeout=60000)
            print("🌐 Navigated to login page.")

            page.fill("input[name='username']", email)
            page.fill("input[id='id_password']", password)
            page.click("button[type='submit']")

            # Wait for dashboard
            page.wait_for_url("**/dashboard", timeout=60000)
            print("✅ Login successful! Current URL:", page.url)

            # Step 2: Navigate to My Suppliers
            print("📋 Step 1: Clicking 'My Suppliers' button in sidebar...")
            page.wait_for_selector('button:has-text("My Suppliers")', timeout=30000)
            page.click('button:has-text("My Suppliers")', force=True)
            print("✅ 'My Suppliers' button clicked")

            # Wait for page to load
            time.sleep(5)

            # Verify navigation was successful
            print("🔍 Verifying My Suppliers page loaded...")
            page.wait_for_selector('button[ng-click="vm.createCsv()"]', timeout=30000)
            print("✅ My Suppliers page loaded successfully")

            # Step 3: Download CSV
            print("📥 Looking for download button...")
            download_button_selector = 'button[ng-click="vm.createCsv()"]'
            page.wait_for_selector(download_button_selector, timeout=30000)

            # Check if button is disabled
            is_disabled = page.get_attribute(download_button_selector, "aria-disabled")
            if is_disabled == "true":
                raise RuntimeError(
                    "❌ Download button is disabled. CSV might still be loading."
                )

            print("🚀 Initiating CSV download...")

            # Click download button and capture the download
            with page.expect_download() as download_info:
                page.click(download_button_selector, force=True)
                print("✅ Download button clicked")

            download = download_info.value
            time.sleep(3)

            # Step 4: Save file with timestamp
            current_datetime = datetime.now()
            temp_dir = Path("/tmp") if os.path.exists("/tmp") else Path(".")
            temp_file = temp_dir / f"vendors_list_temp_{current_datetime.strftime('%Y%m%d_%H%M%S')}.csv"

            download.save_as(str(temp_file))
            print(f"✅ Vendors CSV downloaded: {temp_file}")

            # Step 5: Add data_version column
            with open(temp_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Add data_version to header
            lines[0] = lines[0].rstrip('\n\r') + ',data_version\r\n'
            # Add data_version value to each data row
            timestamp_str = str(current_datetime)
            for i in range(1, len(lines)):
                # Remove trailing whitespace and line endings
                line = lines[i].rstrip('\n\r')
                # Remove trailing comma if it exists (empty last field)
                if line.endswith(','):
                    line = line.rstrip(',')
                # Add quoted timestamp to maintain CSV format
                lines[i] = line + f',"{timestamp_str}"\r\n'
            # Write back
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(":white_check_mark: Added 'data_version' column to vendors CSV.")

            local_file_path = str(temp_file)

            # Step 6: Upload to S3 if enabled
            if upload_to_s3 and s3_bucket:
                s3_path = upload_to_s3_bucket(
                    local_file_path, s3_bucket, current_datetime
                )
                print(f"☁️ File uploaded to S3: {s3_path}")
                result = {
                    "ok": True,
                    "message": "Vendor data scraped and uploaded to S3.",
                    "local_path": local_file_path,
                    "s3_path": s3_path,
                }
            else:
                result = {
                    "ok": True,
                    "message": "Vendor data scraped successfully (local only).",
                    "local_path": local_file_path,
                }

            return result

        except PlaywrightTimeoutError as e:
            print(f"⚠️ Timeout occurred: {e}")
            raise
        except Exception as e:
            print(f"💥 Scraping failed: {e}")
            try:
                page.screenshot(path="vendor_scraping_error.png")
                print("📸 Error screenshot saved: vendor_scraping_error.png")
            except:
                pass
            raise
        finally:
            if browser:
                try:
                    browser.close()
                    print("🧹 Browser closed successfully.")
                except Exception as e:
                    print(f"⚠️ Error closing browser: {e}")


# ---------- S3 Upload Function ----------
def upload_to_s3_bucket(local_file_path, s3_bucket, upload_datetime):
    """
    Upload the CSV file to S3 with date-based folder structure:
    s3://bucket/supply_note/vendor_data/source/vendors_list_YYYYMMDD_HHMMSS.csv
    """
    try:
        # Parse bucket name - extract just the bucket name
        s3_input = s3_bucket.replace("s3://", "").strip("/")
        
        # Get only the bucket name (first part before any /)
        bucket_name = s3_input.split("/")[0]
        
        # Create S3 path with date structure
        year = upload_datetime.strftime("%Y")
        month = upload_datetime.strftime("%m")
        day = upload_datetime.strftime("%d")
        filename = f"vendors_list_{upload_datetime.strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Path: supply_note/vendor_data/YYYY/MM/DD/
        s3_key = f"supply_note/vendor_data/source/{filename}"

        print(f"📤 Uploading to S3: s3://{bucket_name}/{s3_key}")

        # Initialize S3 client with credentials from environment
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
            region_name=os.getenv("S3_BUCKET_REGION", "ap-south-1")
        )

        # Upload file
        s3_client.upload_file(local_file_path, bucket_name, s3_key)

        full_s3_path = f"s3://{bucket_name}/{s3_key}"
        print(f"✅ Successfully uploaded to: {full_s3_path}")

        return full_s3_path

    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        raise


# ---------- Lambda entrypoint ----------
def handler(event=None, context=None):
    """
    AWS Lambda handler.
    Expects environment variables:
    - SUPPLYNOTE_EMAIL
    - SUPPLYNOTE_PASSWORD
    - S3_BUCKET
    """
    print("🚀 Starting Vendor Data scraping (Lambda)...")

    # Get credentials from environment or event
    if event:
        email = event.get("email") or os.getenv("SUPPLYNOTE_EMAIL", "")
        password = event.get("password") or os.getenv("SUPPLYNOTE_PASSWORD", "")
        s3_bucket = event.get("s3_bucket") or os.getenv("S3_BUCKET", "")
        headless = event.get("headless", True)
    else:
        email = os.getenv("SUPPLYNOTE_EMAIL", "")
        password = os.getenv("SUPPLYNOTE_PASSWORD", "")
        s3_bucket = os.getenv("S3_BUCKET", "")
        headless = True

    if not email or not password:
        msg = "❌ Missing credentials: set SUPPLYNOTE_EMAIL and SUPPLYNOTE_PASSWORD"
        print(msg)
        return {"statusCode": 400, "body": msg}

    if not s3_bucket:
        msg = "❌ Missing S3_BUCKET environment variable"
        print(msg)
        return {"statusCode": 400, "body": msg}

    try:
        result = scrape_vendor_data(
            email,
            password,
            headless=headless,
            upload_to_s3=True,
            s3_bucket=s3_bucket,
            is_lambda=True,
        )
        print("🎉 Vendor data scraping completed successfully.")
        return {"statusCode": 200, "body": result}
    except Exception as e:
        print(f"❌ Lambda execution failed: {e}")
        return {"statusCode": 500, "body": f"Error: {e}"}


# ---------- Local runner ----------
def run_local(args):
    """
    Local runner to facilitate testing and debugging.
    Uses .env for creds by default, but CLI args override.
    """
    load_dotenv()  # loads local .env if present

    email = args.email or os.getenv("SUPPLYNOTE_EMAIL", "")
    password = args.password or os.getenv("SUPPLYNOTE_PASSWORD", "")
    s3_bucket = args.s3_bucket or os.getenv("S3_BUCKET", "")

    if not email or not password:
        raise ValueError(
            "Please set SUPPLYNOTE_EMAIL and SUPPLYNOTE_PASSWORD (either env or CLI)."
        )

    # Determine if we should upload to S3
    upload_to_s3 = args.upload_to_s3 and bool(s3_bucket)

    if args.upload_to_s3 and not s3_bucket:
        print(
            "⚠️ Warning: --upload-to-s3 specified but S3_BUCKET not set. Skipping S3 upload."
        )
        upload_to_s3 = False

    headless = args.headless
    print(f"🧪 Running vendor scraper locally (headless={headless})...")
    print(f"📤 S3 Upload: {'Enabled' if upload_to_s3 else 'Disabled'}")

    result = scrape_vendor_data(
        email,
        password,
        headless=headless,
        base_url=args.base_url,
        upload_to_s3=upload_to_s3,
        s3_bucket=s3_bucket,
        is_lambda=False,
    )

    print("\n" + "=" * 50)
    print("✅ SCRAPING COMPLETED")
    print("=" * 50)
    if result.get("local_path"):
        print(f"📁 Local file: {result['local_path']}")
    if result.get("s3_path"):
        print(f"☁️ S3 location: {result['s3_path']}")
    print("=" * 50)


# ---------- CLI ----------
def build_argparser():
    parser = argparse.ArgumentParser(
        description="SupplyNote Vendor Data Scraper (local runner)"
    )
    parser.add_argument("--email", help="SupplyNote email (overrides env)")
    parser.add_argument("--password", help="SupplyNote password (overrides env)")
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode locally",
    )
    parser.add_argument(
        "--base-url", default="https://supplynote.in", help="Base URL for testing"
    )
    parser.add_argument(
        "--upload-to-s3",
        action="store_true",
        default=False,
        help="Upload CSV to S3 after scraping",
    )
    parser.add_argument(
        "--s3-bucket", help="S3 bucket for upload (overrides env S3_BUCKET)"
    )
    return parser


if __name__ == "__main__":
    parser = build_argparser()
    args = parser.parse_args()

    try:
        run_local(args)
    except Exception as exc:
        print(f"❌ Local run failed: {exc}")
        raise