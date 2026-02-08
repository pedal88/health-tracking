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
        # Check if sheet is empty OR if the first cell looks like data (e.g. a date) instead of a header
        first_cell = self.wks.acell("A1").value
        
        # If empty or starts with "20" (assuming date format YYYY-MM-DD), likely missing headers
        if not first_cell or (first_cell and first_cell.startswith("20")):
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
            if not first_cell:
                # Completely empty sheet
                self.wks.append_row(headers, value_input_option="USER_ENTERED")
            else:
                # Data exists but no headers, insert at top
                self.wks.insert_row(headers, index=1, value_input_option="USER_ENTERED")
            
        self.wks.append_row(data_row, value_input_option="USER_ENTERED")
