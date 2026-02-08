import gspread
import logging
from typing import List, Any, Dict

class SheetsProvider:
    def __init__(self, sheet_id: str, credentials: Dict):
        # Authenticate using the dictionary from GH Secrets
        self.gc = gspread.service_account_from_dict(credentials)
        self.sh = self.gc.open_by_key(sheet_id)
        self.wks = self.sh.get_worksheet(0)

    def append_metrics(self, data_row: List[Any]):
        # Define Headers
        headers = [
            "Date", "Body Battery", "BB High/Low", "Exercise?", "Type", "HRV (Last Night)", 
            "Resting Heart Rate", "Stress Avg", "Respiration Avg", "SpO2 Avg", "Weight", 
            "Fitness Age", "Training Status", "Sleep Score", "Sleep Hours", "Deep Sleep (s)", 
            "Light Sleep (s)", "REM Sleep (s)", "Awake (s)", "Steps", "Distance (m)", 
            "Intensity Min (Mod)", "Intensity Min (Vig)", "Active Cals", "BMR Cals", "Total Cals", 
            "Body Battery (Charge/Drain)", "Stress Duration (Low/Med/High)", "Sleep Start", 
            "Sleep End", "Restless Moments", "HRV Status", "Respiration (High/Low)", "VO2 Max",
            "Load Focus (Low/High/Anaerobic)"
        ]

        # 1. Inspect Row 1 to see if headers exist
        try:
            a1_val = self.wks.acell("A1").value
        except:
            a1_val = ""
            
        headers_written = False
        if a1_val != "Date":
            logging.info("Headers missing (A1 != 'Date'), writing headers to A1...")
            self.wks.update("A1", [headers], value_input_option="USER_ENTERED")
            headers_written = True
        
        # 2. Find next available row
        col_a = self.wks.col_values(1)
        # FORCE consistency: if we just wrote headers, we have at least 1 row.
        # The API might be stale and return 0.
        current_rows = len(col_a)
        if headers_written and current_rows == 0:
            logging.info("API stale after header write, forcing next_row=2")
            next_row = 2
        else:
            next_row = current_rows + 1
        
        # 3. Write data to the specific row range (e.g. "A5")
        range_start = f"A{next_row}"
        logging.info(f"Appending data to {range_start} (Row len: {len(data_row)})...")
        self.wks.update(range_start, [data_row], value_input_option="USER_ENTERED")
