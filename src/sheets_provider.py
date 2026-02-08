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
        # We simply check if A1 is "Date". If not, we insert headers.
        try:
            a1_val = self.wks.acell("A1").value
        except:
            a1_val = ""
            
        if a1_val != "Date":
            # Headers are missing or overwritten
            print("Headers missing (A1 is not 'Date'), inserting...")
            self.wks.insert_row(headers, index=1, value_input_option="USER_ENTERED")
            # If the sheet was completely empty, we now have headers at 1.
            # Next data should go to 2.
            
        # 2. Find next available row
        # We rely on Column A (Date) being populated.
        col_a = self.wks.col_values(1) # This now includes "Date" at A1
        next_row = len(col_a) + 1
        
        # 3. Insert/Append at specific row to ensure alignment
        self.wks.insert_row(data_row, index=next_row, value_input_option="USER_ENTERED")
