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
            "Body Fat", "Muscle Mass", "Bone Mass", "Water %",
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
        
        # 2. Check for missing columns and update headers if needed
        # Identify which default headers are missing from existing_headers
        missing_headers = [h for h in default_headers if h not in existing_headers]
        
        # Also check if the data_dict has keys that are not in existing_headers (dynamic expansion)
        # (Optional, but good for future proofing if we add more metrics later without updating default_headers)
        # For now, let's stick to default_headers as the source of truth for order.
        
        if missing_headers:
            logging.info(f"Found missing columns: {missing_headers}. Appending to sheet...")
            # We need to find the next empty column.
            # col_values(1) gives rows in col A. row_values(1) gives cols in row 1.
            # We already have existing_headers which is row_values(1).
            
            # The API allows appending to a row.
            # If existing_headers is ["A", "B"], and we want to add "C", "D".
            # We can update cells starting from len(existing_headers) + 1.
            
            start_col_index = len(existing_headers) + 1
            # Convert index to A1 notation? gspread update can take (row, col).
            # update(range_name, values) or update_cell(row, col, val)
            # update([row], range_name=...)
            
            # Let's use `update` with range. 
            # Or simpler: just read the whole row 1, extend it, and write it back?
            # Writing back the whole row 1 is safer to ensure order is preserved if we were reordering, 
            # but here we just want to append.
            
            # Actually, to be safe and simple:
            # 1. Add missing headers to our local list `existing_headers`.
            # 2. Write the *new* headers to the sheet at the end.
            
            last_col_idx = len(existing_headers)
            # gspread 6.0+ might need named args or specific calls.
            # wks.update_cell(row, col, value) is one by one.
            # wks.update([values], range)
            
            # Helper to convert col index to A1? gspread.utils.rowcol_to_a1 exists but maybe internal.
            # Let's just re-write the entire header row. It's 1 row, low cost.
            
            new_full_headers = existing_headers + missing_headers
            self.wks.update(range_name="A1", values=[new_full_headers])
            
            # Update our local reference
            existing_headers = new_full_headers
            logging.info("Headers updated.")

        # 3. Map data_dict to the sheet's column order
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
