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
from datetime import datetime, timedelta


# ---------- Core scraper (reusable) ----------
def scrape_grn_data(
    email,
    password,
    headless=True,
    base_url="https://supplynote.in",
    upload_to_s3=True,
    s3_bucket=None,
    is_lambda=False,
):
    """
    Core Playwright logic for Item Wise GRN report scraping.
    Reusable by both Lambda and local entrypoints.
    """
    # Determine launch args based on environment
    if is_lambda or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
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
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]

    with sync_playwright() as p:
        print(f"🧠 Launching Chromium (headless={headless}) for GRN scraping...")
        browser = None
        local_file_path = None

        try:
            print(f"🔧 Launch args: {len(launch_args)} arguments configured")
            browser = p.chromium.launch(
                headless=headless,
                args=launch_args,
                timeout=120000,
                slow_mo=100 if not headless else 0,
            )
            
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            page.set_default_timeout(60000)
            print("✅ Browser launched successfully")

            # Step 1: Login
            login_url = f"{base_url}/signin"
            page.goto(login_url, timeout=60000)
            print("🌐 Navigated to login page.")

            page.fill("input[name='username']", email)
            page.fill("input[id='id_password']", password)
            page.click("button[type='submit']")

            page.wait_for_url("**/dashboard", timeout=60000)
            print("✅ Login successful! Current URL:", page.url)

            # Step 2: Navigate to Reports
            print("📊 Step 1: Clicking Reports button in sidebar...")
            page.click('button:has-text("Reports")', force=True)
            print("✅ Reports button clicked")
            time.sleep(3)

            # Step 3: Click Item Wise GRN Report V2
            print("📋 Step 2: Clicking Item Wise GRN Report V2 card...")
            page.click('[ui-sref="reports.itemWiseGRN"]', force=True)
            print("✅ Item Wise GRN card clicked")
            time.sleep(10)

            # Step 4: Set date range (FROM = 1 hour back, TO = current time)
            print("📅 Setting date range...")
            
            # Get current date and time
            current_datetime = datetime.now()
            
            # TO = Current time
            to_datetime = current_datetime
            
            # FROM = Go back 1 hour, rounded to previous hour
            from_datetime = current_datetime - timedelta(hours=1)
            from_datetime = from_datetime.replace(minute=0, second=0, microsecond=0)
            to_datetime = from_datetime.replace(minute=59, second=0, microsecond=0)
            
            print(f"   FROM: {from_datetime.strftime('%d/%m/%Y %I:%M %p')}")
            print(f"   TO: {to_datetime.strftime('%d/%m/%Y %I:%M %p')}")
            
            try:
                # Access iframe
                iframe_element = page.wait_for_selector("iframe.ng-isolate-scope", timeout=10000)
                frame = iframe_element.content_frame()
                
                # Wait for calendar to be ready
                frame.wait_for_selector('p-calendar[formcontrolname="fromDate"]', timeout=10000)
                time.sleep(2)
                
                # === SET FROM DATE-TIME by filling the input directly ===
                print("   Setting FROM date and time...")
                from_calendar_button = frame.locator('p-calendar[formcontrolname="fromDate"] button.p-datepicker-trigger')
                from_calendar_button.click()
                time.sleep(2)
                
                

                frame.wait_for_selector('div.p-timepicker', timeout=10000)
                time.sleep(1)
                
                # Now the time picker should be visible
                # Set HOUR for FROM
                target_hour = int(from_datetime.strftime("%I"))  # 12-hour format
                print(f"   Setting FROM hour to: {target_hour}")
                
                # Get current hour value
                hour_span = frame.locator('div.p-hour-picker span').first
                hour_span.wait_for(state="visible", timeout=5000)
                current_hour = int(hour_span.inner_text())
                
                # Calculate clicks needed
                hour_up_button = frame.locator('div.p-hour-picker button').first
                hour_down_button = frame.locator('div.p-hour-picker button').last
                
                if target_hour > current_hour:
                    clicks = target_hour - current_hour
                    for _ in range(clicks):
                        hour_up_button.click()
                        time.sleep(0.3)
                elif target_hour < current_hour:
                    clicks = current_hour - target_hour
                    for _ in range(clicks):
                        hour_down_button.click()
                        time.sleep(0.3)
                
                print(f"   ✅ FROM hour set to: {target_hour}")
                
                # Set MINUTES for FROM (00)
                print(f"   Setting FROM minutes to: 00")
                minute_span = frame.locator('div.p-minute-picker span').first
                current_minutes = int(minute_span.inner_text())
                
                minute_down_button = frame.locator('div.p-minute-picker button').last
                # Click down to get to 00
                for _ in range(current_minutes):
                    minute_down_button.click()
                    time.sleep(0.2)
                
                print(f"   ✅ FROM minutes set to: 00")
                
                # Set AM/PM for FROM
                target_ampm = from_datetime.strftime("%p")
                print(f"   Setting FROM AM/PM to: {target_ampm}")
                
                ampm_span = frame.locator('div.p-ampm-picker span').first
                current_ampm = ampm_span.inner_text()
                
                if current_ampm != target_ampm:
                    ampm_toggle_button = frame.locator('div.p-ampm-picker button').first
                    ampm_toggle_button.click()
                    time.sleep(0.5)
                
                print(f"   ✅ FROM AM/PM set to: {target_ampm}")

                # Click on today's date
                from_day = from_datetime.day
                from_date_cell = frame.locator(f'td:not(.p-datepicker-other-month) span:has-text("{from_day}")').first
                from_date_cell.click()
                time.sleep(1)
                
                # Close the FROM calendar
                frame.click("body", position={"x": 10, "y": 10})
                time.sleep(2)
                print(f"   ✅ FROM date-time complete")

                print("   Setting TO date and time...")
                
                # Click calendar button to open TO date picker
                to_calendar_button = frame.locator('p-calendar[formcontrolname="toDate"] button.p-datepicker-trigger')
                to_calendar_button.click()
                time.sleep(2)
                
                


                frame.wait_for_selector('div.p-timepicker', timeout=10000)
                time.sleep(1)
                
                # Set HOUR for TO (same as FROM)
                target_hour = int(to_datetime.strftime("%I"))
                print(f"   Setting TO hour to: {target_hour}")
                
                hour_span = frame.locator('div.p-hour-picker span').first
                hour_span.wait_for(state="visible", timeout=5000)
                current_hour = int(hour_span.inner_text())
                
                hour_up_button = frame.locator('div.p-hour-picker button').first
                hour_down_button = frame.locator('div.p-hour-picker button').last
                
                if target_hour > current_hour:
                    clicks = target_hour - current_hour
                    for _ in range(clicks):
                        hour_up_button.click()
                        time.sleep(0.3)
                elif target_hour < current_hour:
                    clicks = current_hour - target_hour
                    for _ in range(clicks):
                        hour_down_button.click()
                        time.sleep(0.3)
                
                print(f"   ✅ TO hour set to: {target_hour}")
                
                # Set MINUTES for TO (59)
                target_minutes = 59
                print(f"   Setting TO minutes to: {target_minutes}")
                
                minute_span = frame.locator('div.p-minute-picker span').first
                current_minutes = int(minute_span.inner_text())
                
                minute_up_button = frame.locator('div.p-minute-picker button').first
                minute_down_button = frame.locator('div.p-minute-picker button').last
                
                if target_minutes > current_minutes:
                    clicks = target_minutes - current_minutes
                    for _ in range(clicks):
                        minute_up_button.click()
                        time.sleep(0.2)
                elif target_minutes < current_minutes:
                    clicks = current_minutes - target_minutes
                    for _ in range(clicks):
                        minute_down_button.click()
                        time.sleep(0.2)
                
                print(f"   ✅ TO minutes set to: 59")
                
                # Set AM/PM for TO
                target_ampm = to_datetime.strftime("%p")
                print(f"   Setting TO AM/PM to: {target_ampm}")
                
                ampm_span = frame.locator('div.p-ampm-picker span').first
                current_ampm = ampm_span.inner_text()
                
                if current_ampm != target_ampm:
                    ampm_toggle_button = frame.locator('div.p-ampm-picker button').first
                    ampm_toggle_button.click()
                    time.sleep(0.5)
                
                print(f"   ✅ TO AM/PM set to: {target_ampm}")

                # Click on today's date
                to_day = to_datetime.day
                to_date_cell = frame.locator(f'td:not(.p-datepicker-other-month) span:has-text("{to_day}")').first
                to_date_cell.click()
                time.sleep(1)
                
                # Close the TO calendar
                frame.click("body", position={"x": 10, "y": 10})
                time.sleep(2)
                print(f"   ✅ TO date-time complete")
                
                print("✅ Date range set successfully")
                
            except Exception as e:
                print(f"⚠️ Could not set date range: {e}")
                import traceback
                traceback.print_exc()
                print("⚠️ Using default date range")

            # Step 5: Work with iframe
            print("🖼️ Accessing iframe...")
            iframe_element = page.wait_for_selector("iframe.ng-isolate-scope", timeout=60000)
            frame = iframe_element.content_frame()
            print("✅ Iframe accessed successfully")

            # Step 6: Select all locations
            print("🔍 Starting filter selection...")
            time.sleep(1)
            
            try:
                print("📍 Looking for Location dropdown inside iframe...")
                frame.wait_for_selector('p-multiselect[formcontrolname="outlets"]', timeout=10000)

                multiselect_button = frame.locator('p-multiselect[formcontrolname="outlets"]')
                multiselect_button.click(force=True)
                print("✅ Location dropdown opened")
                time.sleep(2)

                print("☑️ Looking for Select All checkbox...")
                select_all_checkbox = frame.locator('div[role="checkbox"].p-checkbox-box').first
                select_all_checkbox.wait_for(state="visible", timeout=10000)
                select_all_checkbox.scroll_into_view_if_needed()
                time.sleep(1)

                select_all_checkbox.click(force=True)
                print("✅ Clicked Select All checkbox - all locations selected!")
                time.sleep(2)

                frame.click("body", force=True)
                time.sleep(1)
                print("✅ Filter selection completed")

            except Exception as e:
                print(f"⚠️ Location selection error: {e}")

            
            # Step 8: Generate Report
            print("🚀 Looking for Generate Report button...")
            time.sleep(1)

            iframe_element = page.wait_for_selector("iframe.ng-isolate-scope")
            frame = iframe_element.content_frame()

            frame.wait_for_selector("span.p-button-label", timeout=180000)
            button = frame.locator("span.p-button-label", has_text="Generate Report")
            button.wait_for(state="visible", timeout=10000)
            
            # STEP A: Capture BOTH SN and Reference No BEFORE clicking Generate Report
            print("📊 Capturing current state before generating report...")
            frame.wait_for_selector("tbody.p-datatable-tbody tr", timeout=10000)
            time.sleep(2)
            
            existing_rows = frame.locator("tbody.p-datatable-tbody tr")
            old_row_count = existing_rows.count()
            old_first_sn = None
            old_first_reference = None
            
            if old_row_count > 0:
                try:
                    old_first_row = existing_rows.first
                    
                    # Get Serial Number (1st column - index 0)
                    sn_cell = old_first_row.locator("td").nth(0)
                    old_first_sn = sn_cell.inner_text().strip()
                    
                    # Get Reference Number (2nd column - index 1)
                    ref_cell = old_first_row.locator("td").nth(1)
                    ref_span = ref_cell.locator("span").first
                    old_first_reference = ref_span.inner_text().strip()
                    
                    print(f"📌 Current state: {old_row_count} rows | First row SN: {old_first_sn} | Reference: {old_first_reference}")
                except Exception as e:
                    print(f"⚠️ Could not capture old state: {e}")
            else:
                print("📌 No existing reports in table")
            
            # STEP 8: Click Generate Report
            button.click()
            print("✅ Clicked 'Generate Report' button successfully!")
            time.sleep(3)

            # Step 9: Wait for NEW report with smart polling (check SN + Reference)
            print("⏳ Waiting for NEW report (checking SN + Reference every 30 seconds)...")
            max_wait_time = 600  # 10 minutes
            check_interval = 30
            elapsed_time = 0
            new_report_ready = False

            while elapsed_time < max_wait_time:
                try:
                    print(f"\n🔍 Check #{elapsed_time//30 + 1} - Elapsed: {elapsed_time}s")

                    # Click refresh button to get latest status
                    try:
                        print("   🔄 Clicking refresh button...")
                        frame.wait_for_selector("tbody.p-datatable-tbody tr", timeout=10000)
                        first_row = frame.locator("tbody.p-datatable-tbody tr").first
                        
                        # Find refresh button (has pi-refresh icon)
                        refresh_button = first_row.locator("button:has(span.pi-refresh)")
                        refresh_button.click(force=True)
                        print("   ✅ Refresh clicked")
                        time.sleep(3)  # Wait for table to update
                    except Exception as e:
                        print(f"   ⚠️ Refresh failed: {e}")
                        time.sleep(2)
                    
                    # Wait for table
                    frame.wait_for_selector("tbody.p-datatable-tbody tr", timeout=10000)
                    time.sleep(2)
                    
                    # Get current state
                    current_rows = frame.locator("tbody.p-datatable-tbody tr")
                    current_row_count = current_rows.count()
                    
                    if current_row_count == 0:
                        print("   ⏳ No reports in table yet")
                        time.sleep(check_interval)
                        elapsed_time += check_interval
                        continue
                    
                    first_row = current_rows.first
                    
                    # Get BOTH SN and Reference from first row
                    try:
                        # Serial Number (1st column)
                        sn_cell = first_row.locator("td").nth(0)
                        new_first_sn = sn_cell.inner_text().strip()
                        
                        # Reference Number (2nd column)
                        ref_cell = first_row.locator("td").nth(1)
                        ref_span = ref_cell.locator("span").first
                        new_first_reference = ref_span.inner_text().strip()
                        
                        print(f"   Current: {current_row_count} rows | First row SN: {new_first_sn} | Reference: {new_first_reference}")
                    except Exception as e:
                        print(f"   ⚠️ Could not read row data: {e}")
                        time.sleep(check_interval)
                        elapsed_time += check_interval
                        continue
                    
                    # CHECK 1: Has row count increased? (New row added)
                    row_count_increased = current_row_count > old_row_count
                    
                    # CHECK 2: Is the Reference Number different? (Different report)
                    reference_changed = (new_first_reference != old_first_reference) if old_first_reference else True
                    
                    # CHECK 3: Is Serial Number different? (Confirms new row)
                    sn_changed = (new_first_sn != old_first_sn) if old_first_sn else True
                    
                    print(f"   Row count increased: {row_count_increased} | Reference changed: {reference_changed} | SN changed: {sn_changed}")
                    
                    # If NEW report detected (either count increased OR both SN and Reference changed)
                    is_new_report = row_count_increased or (reference_changed and sn_changed)
                    
                    if is_new_report:
                        print(f"   ✅ NEW report detected! Reference: {new_first_reference}")
                        
                        # Now check if Download button is ready
                        download_button = first_row.locator("span.p-button-label", has_text="Download")
                        
                        if download_button.count() > 0:
                            try:
                                download_button.wait_for(state="visible", timeout=5000)
                                print(f"   ✅ Download button READY! Report is completed.")
                                new_report_ready = True
                                break
                            except:
                                print(f"   ⏳ Download button exists but not visible (Status: Processing)")
                        else:
                            print(f"   ⏳ New report still processing (no download button)")
                    else:
                        print(f"   ⏳ No new report yet")
                    
                    # Wait before next check
                    time.sleep(check_interval)
                    elapsed_time += check_interval
                    
                except Exception as e:
                    print(f"   ❌ Check failed: {str(e)[:100]}")
                    time.sleep(check_interval)
                    elapsed_time += check_interval

            if not new_report_ready:
                raise Exception(f"❌ New report did not complete within {max_wait_time//60} minutes")

            print(f"\n🎉 New report ready! Time taken: {elapsed_time}s ({elapsed_time//60}min {elapsed_time%60}sec)")

            # Step 10: Download the NEW Report
            print("📥 Downloading the NEW report...")
            first_row = frame.locator("tbody.p-datatable-tbody tr").first
            download_button = first_row.locator("span.p-button-label", has_text="Download")
            download_button.wait_for(state="visible", timeout=10000)

            print("⬇️ Clicking Download button for latest report...")
            with page.expect_download() as download_info:
                download_button.click(force=True)

            download = download_info.value
            time.sleep(10)
            

            # Step 10: Save file with timestamp
            current_datetime = datetime.now()
            temp_dir = Path("/tmp") if os.path.exists("/tmp") else Path(".")
            temp_file = temp_dir / f"item_wise_grn_report_temp_{current_datetime.strftime('%Y%m%d_%H%M%S')}.csv"

            download.save_as(str(temp_file))
            print(f"✅ GRN report downloaded: {temp_file}")

            # Step 11: Add data_version column
            df = pd.read_csv(temp_file)
            df["data_version"] = current_datetime
            df.to_csv(temp_file, index=False)
            print("✅ Added 'data_version' column to report")

            local_file_path = str(temp_file)

            # Step 12: Upload to S3 if enabled
            if upload_to_s3 and s3_bucket:
                s3_path = upload_to_s3_bucket(
                    local_file_path, s3_bucket, current_datetime
                )
                print(f"☁️ File uploaded to S3: {s3_path}")
                result = {
                    "ok": True,
                    "message": "Item Wise GRN data scraped and uploaded to S3.",
                    "local_path": local_file_path,
                    "s3_path": s3_path,
                }
            else:
                result = {
                    "ok": True,
                    "message": "Item Wise GRN data scraped successfully (local only).",
                    "local_path": local_file_path,
                }

            return result

        except PlaywrightTimeoutError as e:
            print(f"⚠️ Timeout occurred: {e}")
            raise
        except Exception as e:
            print(f"💥 Scraping failed: {e}")
            try:
                page.screenshot(path="grn_scraping_error.png")
                print("📸 Error screenshot saved: grn_scraping_error.png")
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
    s3://bucket/supply_note/item_wise_grn_data/YYYY/MM/DD/item_wise_grn_report_YYYYMMDD_HHMMSS.csv
    """
    try:
        # Parse bucket name - extract just the bucket name
        s3_input = s3_bucket.replace("s3://", "").strip("/")
        bucket_name = s3_input.split("/")[0]
        
        # Create filename with timestamp
        filename = f"item_wise_grn_report_{upload_datetime.strftime('%Y%m%d_%H%M%S')}.csv"
        
        s3_key = f"supply_note/item_wise_grn_data/source/{filename}"

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
    - EMAIL (for report)
    - S3_BUCKET
    """
    print("🚀 Starting Item Wise GRN scraping (Lambda)...")

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
        result = scrape_grn_data(
            email, password, headless=headless, 
            upload_to_s3=True, s3_bucket=s3_bucket, is_lambda=True
        )
        print("🎉 Item Wise GRN scraping completed successfully.")
        return {"statusCode": 200, "body": result}
    except Exception as e:
        print(f"❌ Lambda execution failed: {e}")
        return {"statusCode": 500, "body": f"Error: {e}"}

# ---------- Local runner ----------
def run_local(args):
    """
    Local runner to facilitate testing and debugging.
    """
    load_dotenv()

    email = args.email or os.getenv("SUPPLYNOTE_EMAIL", "")
    password = args.password or os.getenv("SUPPLYNOTE_PASSWORD", "")
    s3_bucket = args.s3_bucket or os.getenv("S3_BUCKET", "")

    if not email or not password:
        raise ValueError(
            "Please set SUPPLYNOTE_EMAIL and SUPPLYNOTE_PASSWORD (either env or CLI)."
        )

    upload_to_s3 = args.upload_to_s3 and bool(s3_bucket)

    if args.upload_to_s3 and not s3_bucket:
        print("⚠️ Warning: --upload-to-s3 specified but S3_BUCKET not set. Skipping S3 upload.")
        upload_to_s3 = False

    headless = args.headless
    print(f"🧪 Running Item Wise GRN scraper locally (headless={headless})...")
    print(f"📤 S3 Upload: {'Enabled' if upload_to_s3 else 'Disabled'}")

    result = scrape_grn_data(
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
        description="SupplyNote Item Wise GRN Report Scraper"
    )
    parser.add_argument("--email", help="SupplyNote email (overrides env)")
    parser.add_argument("--password", help="SupplyNote password (overrides env)")
    parser.add_argument("--report-email", help="Email for report delivery (overrides env EMAIL)")
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode locally",
    )
    parser.add_argument(
        "--base-url", default="https://supplynote.in", help="Base URL"
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