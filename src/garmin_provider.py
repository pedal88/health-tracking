import logging
from datetime import date
from typing import Dict, Any, List
from garminconnect import Garmin

logger = logging.getLogger(__name__)

class GarminProvider:
    def __init__(self, email: str, password: str):
        self.client = Garmin(email, password)
        self.client.login()

    def fetch_daily_row(self, target_date: date) -> List[Any]:
        d_str = target_date.isoformat()
        
        # Pulling disparate data sources
        stats = self.client.get_stats(d_str)
        sleep = self.client.get_sleep_data(d_str)
        hrv = self.client.get_hrv_data(d_str)
        training = self.client.get_training_status(d_str)
        weight = self.client.get_body_composition(d_str)
        activities = self.client.get_activities(0, 1) # Get most recent

        # Determine Exercise context
        last_act = activities[0] if activities else {}
        is_today = last_act.get("startTimeLocal", "").startswith(d_str)
        
        # Map raw data to your specific list
        sleep_dto = sleep.get("dailySleepDTO", {})
        
        return [
            d_str,                                              # Date
            stats.get("bodyBatteryMostRecentValue"),            # Body Battery
            f"{stats.get('bodyBatteryHighestValue')}/{stats.get('bodyBatteryLowestValue')}", # BB High/Low
            "Yes" if is_today else "No",                        # Exercise (Yes/No)
            last_act.get("activityType", {}).get("typeKey") if is_today else "None", # Type
            hrv.get("hrvSummary", {}).get("lastNightAvg"),      # HRV
            stats.get("restingHeartRate"),                      # RHR
            stats.get("averageStressLevel"),                    # Stress
            stats.get("avgWakingRespirationValue"),             # Respiration
            stats.get("avgOxygenSaturation"),                   # Pulse Ox (SpO2)
            weight.get("totalWeight"),                          # Weight
            training.get("fitnessAge"),                         # Fitness Age
            training.get("trainingStatus"),                     # Training Status
            sleep_dto.get("sleepScore") or sleep_dto.get("sleepScores", {}).get("overall", {}).get("value"), # Sleep Score
            round(sleep_dto.get("sleepTimeSeconds", 0)/3600, 2), # Duration (Hours)
            sleep_dto.get("deepSleepSeconds"),                  # Deep
            sleep_dto.get("lightSleepSeconds"),                 # Light
            sleep_dto.get("remSleepSeconds"),                   # REM
            sleep_dto.get("awakeSleepSeconds")                  # Awake
        ]
