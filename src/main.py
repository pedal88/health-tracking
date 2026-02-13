import os
import sys
import json
import logging
from datetime import date, timedelta
from garmin_provider import GarminProvider
from sheets_provider import SheetsProvider
from utils import load_historical_weights

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_date(target_date, garmin, sheets, history_weights):
    """
    Fetches and syncs data for a single date.
    Returns True if data was "complete" (has Sleep Score), False otherwise.
    """
    logger.info(f"--- Processing data for {target_date} ---")
    try:
        # 1. Fetch from Garmin
        row = garmin.fetch_daily_row(target_date)
        
        # 2. Check for Historical Weight CSV (Override)
        csv_weight = history_weights.get(target_date)
        if csv_weight is not None:
            logger.info(f"Found historical weight for {target_date}: {csv_weight}kg. Overriding Garmin data.")
            row["Weight"] = csv_weight
            
        # 3. Always UPSERT data first
        sheets.append_metrics(row)
        logger.info(f"Successfully synced available data for {target_date}.")

        # 4. Check for Completeness
        has_sleep = row.get("Sleep Score") is not None
        if not has_sleep:
             logger.warning(f"Sleep Score missing for {target_date}. Data likely incomplete. Will retry on next run.")
             return False
        
        return True

    except Exception as e:
        logger.error(f"Failed to process {target_date}: {e}")
        return False

def main():
    try:
        # ... setup env ...
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Validate required environment variables
        required_vars = ["GARMIN_EMAIL", "GARMIN_PASSWORD", "GOOGLE_SHEET_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
            sys.exit(1)

        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if creds_json:
            try:
                creds = json.loads(creds_json)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON")
                sys.exit(1)
        elif os.path.exists("service_account.json"):
            logger.info("Using service_account.json file")
            with open("service_account.json", "r") as f:
                creds = json.load(f)
        else:
             logger.error("No credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON or create service_account.json")
             sys.exit(1)
        
        garmin = GarminProvider(os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
        sheets = SheetsProvider(os.getenv("GOOGLE_SHEET_ID"), creds)

        # Load Weights once
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "historical_weight.csv")
        history_weights = {}
        try:
             history_weights = load_historical_weights(csv_path)
        except Exception as e:
             logger.warning(f"Failed to load historical weights: {e}")

        # Process Today AND Yesterday to catch late syncs
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # We process yesterday first, then today
        days_to_process = [yesterday, today]
        
        for d in days_to_process:
            process_date(d, garmin, sheets, history_weights)
            
    except Exception as e:
        logger.error(f"Pipeline Error: {e}", exc_info=True)
        # We don't exit(1) here anymore because if one day fails, we still want the job to 'pass' 
        # so the scheduler keeps running without alerting the user every time.
        # Unless it's a critical auth error which would have been caught in setup.
        sys.exit(1)

if __name__ == "__main__":
    main()
