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
        # Check if sheet is empty (no headers) and add them if needed
        if not self.wks.get_values("A1"):
            headers = [
                "Date", "Body Battery", "BB High/Low", "Exercise?", "Type", "HRV (Last Night)", 
                "Resting Heart Rate", "Stress Avg", "Respiration Avg", "SpO2 Avg", "Weight", 
                "Fitness Age", "Training Status", "Sleep Score", "Sleep Hours", "Deep Sleep (s)", 
                "Light Sleep (s)", "REM Sleep (s)", "Awake (s)"
            ]
            self.wks.append_row(headers, value_input_option="USER_ENTERED")
            
        self.wks.append_row(data_row, value_input_option="USER_ENTERED")
