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

        
        # Advanced Metrics
        readiness_list = None
        try:
            readiness_list = self.client.get_training_readiness(d_str)
        except Exception:
            pass
            
        hrv_data = None
        try:
            hrv_data = self.client.get_hrv_data(d_str)
        except Exception:
            pass

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
        load_focus_vals = {'low': 0, 'high': 0, 'anaerobic': 0}
        
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
            # Structure: training -> mostRecentTrainingLoadBalance -> metricsTrainingLoadBalanceDTOMap -> {deviceId: { ... }}
            lb_root = training.get("mostRecentTrainingLoadBalance", {})
            lb_data = lb_root.get("metricsTrainingLoadBalanceDTOMap", {})

            for device_id, device_data in lb_data.items():
                low = device_data.get("monthlyLoadAerobicLow", 0)
                high = device_data.get("monthlyLoadAerobicHigh", 0)
                anaerobic = device_data.get("monthlyLoadAnaerobic", 0)
                
                # If we find valid data, capture it
                if low or high or anaerobic:
                    load_focus_vals = {
                        'low': int(low),
                        'high': int(high),
                        'anaerobic': int(anaerobic)
                    }
                    # load_focus kept for backward compatibility if needed
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
                start_ts = (sleep_dto.get("sleepStartTimestampLocal") or 0) / 1000
                end_ts = (sleep_dto.get("sleepEndTimestampLocal") or 0) / 1000
                sleep_start = datetime.datetime.fromtimestamp(start_ts).strftime('%H:%M')
                sleep_end = datetime.datetime.fromtimestamp(end_ts).strftime('%H:%M')
        except:
            pass
            
        # Worn Logic (Activity + Pulse)
        total_steps = stats.get("totalSteps") or 0
        rhr = stats.get("restingHeartRate")
        
        is_worn = "No"
        if total_steps > 0 or rhr:
             is_worn = "Yes"

        
        # --- EXTRACT ADVANCED METRICS ---
        
        # 1. Readiness & Recovery
        readiness_score = None
        readiness_feedback = None
        recovery_time_hours = None
        
        if readiness_list and isinstance(readiness_list, list):
            # Index 0 is usually the latest
            latest = readiness_list[0]
            readiness_score = latest.get("score")
            readiness_feedback = latest.get("feedbackShort") # "PRIME_TO_TRAIN"
            
            # Recovery time is in minutes in readiness response
            # e.g. 2161 mins = 36 hours
            if latest.get("recoveryTime") is not None:
                recovery_time_hours = round(latest.get("recoveryTime") / 60, 1)
        
        # 2. Acute Load
        acute_load = None
        if training:
            # mostRecentTrainingStatus -> latestTrainingStatusData -> {deviceId} -> acuteTrainingLoadDTO -> dailyTrainingLoadAcute
            ts_root = training.get("mostRecentTrainingStatus") or {}
            ts_items = ts_root.get("latestTrainingStatusData") or {}
            for _, dev_data in ts_items.items():
                load_dto = dev_data.get("acuteTrainingLoadDTO")
                if load_dto:
                    acute_load = load_dto.get("dailyTrainingLoadAcute")
                    break
                    
        # 3. HRV Details
        hrv_weekly = None
        hrv_status_text = None
        if hrv_data:
            summary = hrv_data.get("hrvSummary") or {}
            hrv_weekly = summary.get("weeklyAvg")
            hrv_status_text = summary.get("status") # "BALANCED"
            
        # 4. Skin Temp
        # dailySleepDTO -> avgOvernightTemperatureDeviation
        skin_temp_dev = sleep_dto.get("avgOvernightTemperatureDeviation")
        
        return {
            "Date": d_str,
            "Worn?": is_worn,
            "Body Battery": stats.get("bodyBatteryMostRecentValue"),
            "BB High": stats.get('bodyBatteryHighestValue'),
            "BB Low": stats.get('bodyBatteryLowestValue'),
            "Exercise?": "Yes" if is_today else "No",
            "Type": (last_act.get("activityType") or {}).get("typeKey") if is_today else "None",
            "HRV (Last Night)": (hrv.get("hrvSummary") or {}).get("lastNightAvg"),
            "Resting Heart Rate": stats.get("restingHeartRate"),
            "Stress Avg": stats.get("averageStressLevel"),
            "Respiration Avg": stats.get("avgWakingRespirationValue"),
            "SpO2 Avg": stats.get("avgOxygenSaturation"),
            "Weight": round(((weight.get("totalAverage") or {}).get("weight") or 0) / 1000, 2) if (weight.get("totalAverage") or {}).get("weight") else None,
            "Body Fat": (weight.get("totalAverage") or {}).get("bodyFat"),
            "Muscle Mass": round(((weight.get("totalAverage") or {}).get("muscleMass") or 0) / 1000, 2) if (weight.get("totalAverage") or {}).get("muscleMass") else None,
            "Bone Mass": round(((weight.get("totalAverage") or {}).get("boneMass") or 0) / 1000, 2) if (weight.get("totalAverage") or {}).get("boneMass") else None,
            "Water %": (weight.get("totalAverage") or {}).get("bodyWater"), 
            "Fitness Age": fitness_age,
            "Training Status": training_status,
            "Sleep Score": (sleep_dto.get("sleepScore") if sleep_dto else None) or ((sleep_dto.get("sleepScores") or {}) if sleep_dto else {}).get("overall", {}).get("value"),
            "Sleep Hours": round(((sleep_dto.get("sleepTimeSeconds") or 0) / 3600), 2) if sleep_dto else 0,
            "Deep Sleep (s)": sleep_dto.get("deepSleepSeconds") if sleep_dto else None,
            "Light Sleep (s)": sleep_dto.get("lightSleepSeconds") if sleep_dto else None,
            "REM Sleep (s)": sleep_dto.get("remSleepSeconds") if sleep_dto else None,
            "Awake (s)": sleep_dto.get("awakeSleepSeconds") if sleep_dto else None,
            
            # --- NEW METRICS SPLIT ---
            "Steps": total_steps,
            "Distance (m)": stats.get("totalDistanceMeters"),
            "Intensity Min (Mod)": stats.get("moderateIntensityMinutes"),
            "Intensity Min (Vig)": stats.get("vigorousIntensityMinutes"),
            "Active Cals": stats.get("activeKilocalories"),
            "BMR Cals": stats.get("bmrKilocalories"),
            "Total Cals": stats.get("totalKilocalories"),
            
            "BB Charge": stats.get('bodyBatteryChargedValue'),
            "BB Drain": stats.get('bodyBatteryDrainedValue'),
            
            "Stress Duration Low": round((stats.get('lowStressDuration') or 0)/60),
            "Stress Duration Med": round((stats.get('mediumStressDuration') or 0)/60),
            "Stress Duration High": round((stats.get('highStressDuration') or 0)/60),
            
            "Sleep Start": sleep_start,
            "Sleep End": sleep_end,
            "Restless Moments": sleep_dto.get("restlessMomentsCount"),
            "HRV Status": sleep.get("hrvStatus"),
            
            "Respiration High": stats.get('highestRespirationValue'),
            "Respiration Low": stats.get('lowestRespirationValue'),
            
            "VO2 Max": vo2_max,
            
            "Load Low": load_focus_vals['low'],
            "Load High": load_focus_vals['high'],
            "Load Anaerobic": load_focus_vals['anaerobic'],
            
            # --- ADVANCED METRICS ---
            "Readiness Score": readiness_score,
            "Readiness Status": readiness_feedback,
            "Acute Load": acute_load,
            "Recovery Hours": recovery_time_hours,
            "HRV Weekly": hrv_weekly,
            "HRV Status (Text)": hrv_status_text,
            "Skin Temp Dev": sleep_dto.get("avgOvernightTemperatureDeviation") if sleep_dto else None
        }
