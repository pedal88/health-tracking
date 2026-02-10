import os
import csv
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def load_historical_weights(csv_path: str) -> Dict[Any, float]:
    """
    Parses historical_weight.csv.
    Expected format: "Habit - Date", "Habit Catalog", "Date", "Value"
    Date format: "February 9, 2026"
    Value format: "88,5" or "88.5" or "88"
    """
    weights = {} # { date_obj: float }
    if not os.path.exists(csv_path):
        logger.warning(f"CSV file not found: {csv_path}")
        return weights

    logger.info(f"Loading historical weights from {csv_path}...")
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get("Date")
                val_str = row.get("Value")
                
                if not date_str or not val_str or val_str.strip() == "-" or not val_str.strip():
                    continue

                try:
                    # Parse Date: "February 9, 2026"
                    dt = datetime.strptime(date_str.strip(), "%B %d, %Y").date()
                    
                    # Parse Weight: "88,5" -> 88.5
                    val_clean = val_str.replace(",", ".").strip()
                    weight = float(val_clean)
                    
                    weights[dt] = weight
                except ValueError:
                    pass
    except Exception as e:
        logger.error(f"Failed to parse history file: {e}")
        
    logger.info(f"Loaded {len(weights)} historical weight entries.")
    return weights
