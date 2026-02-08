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

        # 2. Get Training Status & Load Focus (Deep Parse)
        training_status = None
        vo2_max = None
        load_focus = None
        
        try:
            # Training Status & VO2 Max
            # Structure: training -> mostRecentTrainingStatus -> latestTrainingStatusData -> {deviceId: { ... }}
            ts_root = training.get("mostRecentTrainingStatus", {})
            ts_data = ts_root.get("latestTrainingStatusData", {})
            
            # VO2 Max
            vo2_data = training.get("mostRecentVO2Max", {}).get("generic", {})
            vo2_max = vo2_data.get("vo2MaxPreciseValue")

            for device_id, device_data in ts_data.items():
                if device_data.get("trainingStatusFeedbackPhrase"):
                    training_status = device_data.get("trainingStatusFeedbackPhrase")
                    break
            
            # Load Focus
            # Structure: training -> mostRecentTrainingStatus -> definitions -> ... NO
            # Structure: training -> mostRecentTrainingLoadBalance -> metricsTrainingLoadBalanceDTOMap -> {deviceId: { ... }}
            lb_root = training.get("mostRecentTrainingLoadBalance", {})
            lb_data = lb_root.get("metricsTrainingLoadBalanceDTOMap", {})
            for device_id, device_data in lb_data.items():
                low = device_data.get("monthlyLoadAerobicLow", 0)
                high = device_data.get("monthlyLoadAerobicHigh", 0)
                anaerobic = device_data.get("monthlyLoadAnaerobic", 0)
                if low or high or anaerobic:
                    load_focus = f"{int(low)}/{int(high)}/{int(anaerobic)}"
                    break

        except Exception as e:
            logger.debug(f"Failed to parse training status: {e}")

        # Map raw data to your specific list
        sleep_dto = sleep.get("dailySleepDTO", {})
        
        # Sleep Timing (convert ms to HH:MM Local)
        sleep_start = "None"
        sleep_end = "None"
        try:
            if sleep_dto.get("sleepStartTimestampLocal"):
                # Convert 1770502398000 -> timestamp -> string
                # Note: These are timestamps in ms. 
                import datetime
                start_ts = sleep_dto.get("sleepStartTimestampLocal") / 1000
                end_ts = sleep_dto.get("sleepEndTimestampLocal") / 1000
                sleep_start = datetime.datetime.fromtimestamp(start_ts).strftime('%H:%M')
                sleep_end = datetime.datetime.fromtimestamp(end_ts).strftime('%H:%M')
        except:
            pass
            
        return [
            d_str,                                              # Date
            stats.get("bodyBatteryMostRecentValue"),            # Body Battery
            f"{stats.get('bodyBatteryHighestValue')}/{stats.get('bodyBatteryLowestValue')}", # BB High/Low
            "Yes" if is_today else "No",                        # Exercise (Yes/No)
            last_act.get("activityType", {}).get("typeKey") if is_today else "None", # Type
            hrv.get("hrvSummary", {}).get("lastNightAvg"),      # HRV
            stats.get("restingHeartRate"),                      # RHR
            stats.get("averageStressLevel"),                    # Stress
            stats.get("avgWakingRespirationValue"),             # RespirationAvg
            stats.get("avgOxygenSaturation"),                   # Pulse Ox (SpO2)
            weight.get("totalWeight"),                          # Weight
            fitness_age,                                        # Fitness Age
            training_status,                                    # Training Status
            sleep_dto.get("sleepScore") or sleep_dto.get("sleepScores", {}).get("overall", {}).get("value"), # Sleep Score
            round(sleep_dto.get("sleepTimeSeconds", 0)/3600, 2), # Duration (Hours)
            sleep_dto.get("deepSleepSeconds"),                  # Deep
            sleep_dto.get("lightSleepSeconds"),                 # Light
            sleep_dto.get("remSleepSeconds"),                   # REM
            sleep_dto.get("awakeSleepSeconds"),                 # Awake
            
            # --- NEW METRICS ---
            stats.get("totalSteps"),                            # Steps
            stats.get("totalDistanceMeters"),                   # Distance
            stats.get("moderateIntensityMinutes"),              # Intensity Min (Mod)
            stats.get("vigorousIntensityMinutes"),              # Intensity Min (Vig)
            stats.get("activeKilocalories"),                    # Active Cals
            stats.get("bmrKilocalories"),                       # BMR Cals
            stats.get("totalKilocalories"),                     # Total Cals
            f"{stats.get('bodyBatteryChargedValue')}/{stats.get('bodyBatteryDrainedValue')}", # Body Battery (Charge/Drain)
            f"{round(stats.get('lowStressDuration', 0)/60)}/{round(stats.get('mediumStressDuration', 0)/60)}/{round(stats.get('highStressDuration', 0)/60)}", # Stress Duration (Min)
            sleep_start,                                        # Sleep Start
            sleep_end,                                          # Sleep End
            sleep_dto.get("restlessMomentsCount"),              # Restless Moments
            sleep.get("hrvStatus"),                             # HRV Status
            f"{stats.get('highestRespirationValue')}/{stats.get('lowestRespirationValue')}", # Respiration (High/Low)
            vo2_max,                                            # VO2 Max
            load_focus                                          # Load Focus
        ]
