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
START_DATE = date(2024, 3, 20)  # Modify this to your desired start date
END_DATE = date.today() # Include today
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

# ... imports ...
import csv
from utils import load_historical_weights

# ... existing code ...

def main():
    try:
        creds = get_credentials()
        
        if not creds["garmin_email"] or not creds["garmin_password"]:
            logger.error("Garmin credentials missing.")
            return

        # Initialize Providers
        garmin = GarminProvider(creds["garmin_email"], creds["garmin_password"])
        sheets = SheetsProvider(creds["sheet_id"], creds["google_creds"])
        
        # Load Historical Weights
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "historical_weight.csv")
        history_weights = load_historical_weights(csv_path)

        # Fetch existing dates to prevent duplicates
        existing_dates = set(sheets.wks.col_values(1))
        # Note: If we need to Backfill CSV data for DATES THAT EXIST but have no weight, 
        # checking "existing_dates" strictly might prevent updating. 
        # But usually 'append_metrics' just adds rows. Updating existing rows is harder (requires finding row).
        # For now, we assume we are filling holes (missing dates).
        
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
                # We try to fetch regardless, to get Sleep/Activities.
                # If Garmin fails, we handle it.
                data = {}
                try:
                    data = garmin.fetch_daily_row(current_date)
                except Exception as e:
                    logger.warning(f"  - Garmin fetch failed for {date_str}: {e}")
                    # If Garmin fails, we initialize a basic dict so we can potentially fill with CSV weight
                    data = {"Date": date_str, "Worn?": "No", "Exercise?": "No"}

                # 2. Apply CSV Override
                # If we have a weight in CSV, use it.
                csv_weight = history_weights.get(current_date)
                if csv_weight is not None:
                    logger.info(f"  - Found historical weight for {current_date}: {csv_weight}kg")
                    data["Weight"] = csv_weight
                else:
                    # logger.debug(f"  - No historical weight for {current_date} (Available: {list(history_weights.keys())[:3]}...)")
                    pass
                    # If we had no Garmin data, ensure keys exist to prevent Sheets errors (if strictly mapping)
                    # SheetsProvider maps by keys, so missing keys usually just leave cells blank.
                
                # 3. Check Validity
                # Criteria: Must have Sleep Score OR Valid Weight
                has_sleep = data.get("Sleep Score") is not None
                has_weight = data.get("Weight") is not None
                
                if not has_sleep and not has_weight:
                    logger.warning(f"  - No Sleep Score AND No Weight for {date_str}. Skipping save.")
                    continue
                
                # 4. Append to Sheets
                sheets.append_metrics(data)
                logger.info(f"  - Successfully synced {date_str}")

                # 5. Rate Limiting / Politeness
                # Only sleep if we actually hit Garmin successfully to avoid spamming if loop is fast on just CSV
                # But safer to always sleep a little.
                sleep_time = random.uniform(1.0, 3.0) 
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"  - Failed to process {date_str}: {e}", exc_info=True)
                continue

        logger.info("Backfill complete!")

    except KeyboardInterrupt:
        logger.info("Backfill stopped by user.")
    except Exception as e:
        logger.error(f"Fatal Error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
