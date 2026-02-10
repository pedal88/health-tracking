import os
import sys
import json
import logging
from datetime import date
from garmin_provider import GarminProvider
from sheets_provider import SheetsProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    try:
        # Load environment via GH Secrets or .env (if python-dotenv is used locally) 
        # Note: python-dotenv loading is typically done via `load_dotenv()` but user didn't explicitly ask for it in main unless implied.
        # But user listed python-dotenv in requirements.txt so I should probably add it for local dev convenience.
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass # Not required in production/CI context where env vars are injected

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
        row = garmin.fetch_daily_row(today)

        # Logic: If Sleep Score (index 13) is missing, the watch hasn't synced yet.
        if row.get("Sleep Score") is None:
            logger.warning("Metric Sync Incomplete: Sleep Score missing. Exiting for retry...")
            sys.exit(1)

        sheets.append_metrics(row)
        logger.info("Successfully appended data to Google Sheets.")

    except Exception as e:
        logger.error(f"Pipeline Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
