import os
import time
import logging
import random
from datetime import date, timedelta, datetime
from typing import List

from dotenv import load_dotenv

from garmin_provider import GarminProvider
from sheets_provider import SheetsProvider

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
START_DATE = date(2026, 2, 1)  # Modify this to your desired start date
END_DATE = date.today() - timedelta(days=1) # Yesterday
# ---------------------

def get_credentials():
    """
    Load credentials from environment variables or service_account.json.
    """
    load_dotenv()
    
    # Try loading from local file first (dev/backfill mode)
    service_account_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "service_account.json")
    if os.path.exists(service_account_path):
        logger.info("Using service_account.json file")
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = service_account_path # Not strictly used by logic below but good for consistency
        # Load the JSON content manually for the provider
        import json
        with open(service_account_path) as f:
            creds_dict = json.load(f)
    else:
        # Fallback to env var (CI/CD)
        import json
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not creds_json:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not found in env or file")
        creds_dict = json.loads(creds_json)

    return {
        "garmin_email": os.getenv("GARMIN_EMAIL"),
        "garmin_password": os.getenv("GARMIN_PASSWORD"),
        "sheet_id": os.getenv("GOOGLE_SHEET_ID"),
        "google_creds": creds_dict
    }

def date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def main():
    try:
        creds = get_credentials()
        
        if not creds["garmin_email"] or not creds["garmin_password"]:
            logger.error("Garmin credentials missing.")
            return

        # Initialize Providers
        garmin = GarminProvider(creds["garmin_email"], creds["garmin_password"])
        sheets = SheetsProvider(creds["sheet_id"], creds["google_creds"])

        # Fetch existing dates to prevent duplicates
        existing_dates = set(sheets.wks.col_values(1))
        logger.info(f"Found {len(existing_dates)} existing entries in sheet.")

        logger.info(f"Starting backfill from {START_DATE} to {END_DATE}")

        # Iterate
        delta = END_DATE - START_DATE
        for i in range(delta.days + 1):
            current_date = START_DATE + timedelta(days=i)
            date_str = current_date.isoformat()

            if date_str in existing_dates:
                logger.info(f"Skipping {date_str} - Already exists.")
                continue

            logger.info(f"Processing {date_str}...")

            try:
                # 1. Fetch from Garmin
                data = garmin.fetch_daily_row(current_date)
                
                # Check for critical data (Sleep Score)
                # Index 13 is Sleep Score based on the provider list structure
                if data[13] is None:
                    logger.warning(f"  - Missing Sleep Score for {date_str}. Skipping save (or logging partially).")
                    # Option: Continue anyway? Or skip? 
                    # For backfill, we might want to skip mostly empty rows, or save what we have.
                    # Let's save what we have but log a warning.
                
                # 2. Append to Sheets
                # Use the provider wrapper to handle headers and correct row placement
                sheets.append_metrics(data)
                # Note: logging is handled inside append_metrics for data placement, 
                # but we keep this summary log.
                logger.info(f"  - Successfully synced {date_str}")

                # 3. Rate Limiting / Politeness
                sleep_time = random.uniform(2.0, 5.0)
                logger.info(f"  - Sleeping {sleep_time:.2f}s...")
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"  - Failed to process {date_str}: {e}")
                # Continue to next date
                continue

        logger.info("Backfill complete!")

    except KeyboardInterrupt:
        logger.info("Backfill stopped by user.")
    except Exception as e:
        logger.error(f"Fatal Error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
