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
            row1 = self.wks.row_values(1)
        except:
            row1 = []
        
        if not row1:
            # Sheet is empty, add headers
            self.wks.insert_row(headers, index=1, value_input_option="USER_ENTERED")
            # Now append data to row 2
            self.wks.insert_row(data_row, index=2, value_input_option="USER_ENTERED")
            return

        # Check if row1 matches our headers (roughly) or if it looks like data
        # If it looks like data (starts with 20xx-), insert headers at top
        first_cell = row1[0] if row1 else ""
        if first_cell.startswith("20"):
             self.wks.insert_row(headers, index=1, value_input_option="USER_ENTERED")
             # The existing data is pushed down to row 2, 3...
             # Now find where to append new data.
        
        # 2. Find next available row
        # We rely on Column A (Date) being populated.
        col_a = self.wks.col_values(1)
        next_row = len(col_a) + 1
        
        # 3. Insert/Append at specific row to ensure alignment
        # Using insert_row is safer than append_row for alignment if sheet has "ghost" data
        self.wks.insert_row(data_row, index=next_row, value_input_option="USER_ENTERED")
