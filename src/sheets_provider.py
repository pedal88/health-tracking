import gspread
import logging
from typing import List, Any, Dict

class SheetsProvider:
    def __init__(self, sheet_id: str, credentials: Dict):
        # Authenticate using the dictionary from GH Secrets
        self.gc = gspread.service_account_from_dict(credentials)
        self.sh = self.gc.open_by_key(sheet_id)
        self.wks = self.sh.get_worksheet(0)

    def append_metrics(self, data_dict: Dict[str, Any]):
        # 1. Fetch existing headers from the sheet (Row 1)
        # We need to know the *actual* column order to place data correctly.
        existing_headers = self.wks.row_values(1)

        # Default headers if sheet is empty
        default_headers = [
            "Date", "Worn?", "Body Battery", "BB High", "BB Low", "Exercise?", "Type", "HRV (Last Night)", 
            "Resting Heart Rate", "Stress Avg", "Respiration Avg", "SpO2 Avg", "Weight", 
            "Fitness Age", "Training Status", "Sleep Score", "Sleep Hours", "Deep Sleep (s)", 
            "Light Sleep (s)", "REM Sleep (s)", "Awake (s)", "Steps", "Distance (m)", 
            "Intensity Min (Mod)", "Intensity Min (Vig)", "Active Cals", "BMR Cals", "Total Cals", 
            "BB Charge", "BB Drain", "Stress Duration Low", "Stress Duration Med", 
            "Stress Duration High", "Sleep Start", "Sleep End", "Restless Moments", "HRV Status", 
            "Respiration High", "Respiration Low", "VO2 Max",
            "Load Low", "Load High", "Load Anaerobic",
            "Readiness Score", "Readiness Status", "Acute Load", "Recovery Hours",
            "HRV Weekly", "HRV Status (Text)", "Skin Temp Dev"
        ]

        if not existing_headers:
            logging.info("Sheet is empty, writing default headers...")
            self.wks.update("A1", [default_headers], value_input_option="USER_ENTERED")
            existing_headers = default_headers
        
        # 2. Map data_dict to the sheet's column order
        row_values = []
        for header in existing_headers:
            # Get value from dict, default to "" if header not found in our data
            val = data_dict.get(header, "")
            row_values.append(val)

        # 3. Determine where to write
        # We assume column A ("Date") is always populated for valid rows.
        col_a = self.wks.col_values(1)
        
        # Race condition handling:
        # If we just wrote headers, lines might be stale.
        # But since we wrote headers above manually if empty, we know we have at least 1 row.
        
        if not col_a: 
             # Should be caught by "if not existing_headers" but just in case
             next_row = 1 
        else:
             next_row = len(col_a) + 1
             if next_row == 1 and existing_headers:
                 next_row = 2 # Force pass headers if they exist
        
        # 4. Write Data
        range_start = f"A{next_row}"
        
        logging.info(f"Appending data to {range_start} (Matched {len(row_values)} columns)...")
        self.wks.update(range_start, [row_values], value_input_option="USER_ENTERED")
