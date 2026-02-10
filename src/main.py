import os
import sys
import json
import logging
from datetime import date
from garmin_provider import GarminProvider
from sheets_provider import SheetsProvider
from utils import load_historical_weights

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    try:
        # Load environment via GH Secrets or .env
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
        # Fallback to local file for development
        elif os.path.exists("service_account.json"):
            logger.info("Using service_account.json file")
            with open("service_account.json", "r") as f:
                creds = json.load(f)
        else:
             logger.error("No credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON or create service_account.json")
             sys.exit(1)
        
        garmin = GarminProvider(os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
        sheets = SheetsProvider(os.getenv("GOOGLE_SHEET_ID"), creds)

        today = date.today()
        logger.info(f"Fetching data for {today}")
        
        # 1. Fetch from Garmin
        row = garmin.fetch_daily_row(today)
        
        # 2. Check for Historical Weight CSV (Override)
        try:
            # Locate CSV relative to this script
            csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "historical_weight.csv")
            history_weights = load_historical_weights(csv_path)
            csv_weight = history_weights.get(today)
            
            if csv_weight is not None:
                logger.info(f"Found historical weight for today: {csv_weight}kg. Overriding Garmin data.")
                row["Weight"] = csv_weight
        except Exception as e:
            logger.warning(f"Failed to load historical weights: {e}")

        # Logic: If Sleep Score is missing, we usually exit(1) to retry later.
        # NEW LOGIC: If we have a valid Weight from CSV, we allow the sync to proceed.
        
        has_sleep = row.get("Sleep Score") is not None
        has_csv_weight = (history_weights.get(today) is not None) if 'history_weights' in locals() else False
        
        if not has_sleep:
            if has_csv_weight:
                 logger.warning("Sleep Score missing, but CSV weight found. Proceeding with sync.")
            else:
                 logger.warning("Metric Sync Incomplete: Sleep Score missing. Exiting for retry...")
                 sys.exit(1)

        sheets.append_metrics(row)
        logger.info("Successfully appended data to Google Sheets.")

    except Exception as e:
        logger.error(f"Pipeline Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
