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

        if not stats:
            stats = {}
        if not activities:
            activities = []

        # Determine Exercise context
        last_act = activities[0] if activities else {}
        is_today = last_act.get("startTimeLocal", "").startswith(d_str)
        
        # Validate responses
        if not sleep:
            sleep = {}
        if not hrv:
            hrv = {}
        if not training:
            training = {}
        if not weight:
            weight = {}
        
        # 1. Get Fitness Age
        fitness_age = None
        try:
            fa_data = self.client.get_fitnessage_data(d_str)
            if fa_data:
                fitness_age = fa_data.get("fitnessAge")
        except Exception as e:
            logger.debug(f"Failed to fetch fitness age: {e}")

        # 2. Get Training Status (Deep Parse)
        training_status = None
        try:
            # Structure: training -> mostRecentTrainingStatus -> latestTrainingStatusData -> {deviceId: { ... }}
            ts_data = training.get("mostRecentTrainingStatus", {}).get("latestTrainingStatusData", {})
            for device_id, device_data in ts_data.items():
                # Prefer primary device or just take first one
                if device_data.get("trainingStatusFeedbackPhrase"):
                    training_status = device_data.get("trainingStatusFeedbackPhrase")
                    break
        except Exception as e:
            logger.debug(f"Failed to parse training status: {e}")

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
            fitness_age,                                        # Fitness Age
            training_status,                                    # Training Status
            sleep_dto.get("sleepScore") or sleep_dto.get("sleepScores", {}).get("overall", {}).get("value"), # Sleep Score
            round(sleep_dto.get("sleepTimeSeconds", 0)/3600, 2), # Duration (Hours)
            sleep_dto.get("deepSleepSeconds"),                  # Deep
            sleep_dto.get("lightSleepSeconds"),                 # Light
            sleep_dto.get("remSleepSeconds"),                   # REM
            sleep_dto.get("awakeSleepSeconds")                  # Awake
        ]
