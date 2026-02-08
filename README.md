# Health Data Sync

A Python application that automatically fetches your daily health metrics from Garmin Connect and archives them into a Google Sheet.

Designed to run "headless" via GitHub Actions, it includes robust retry logic to ensure data is only captured when your watch has fully synced (e.g., waiting for sleep data).

## Features

- **Comprehensive Metrics**: Captures Sleep Score, Body Battery (High/Low), HRV Status, Resting Heart Rate, Stress, SpO2, Weight, and more.
- **Fail-Fast Logic**: Automatically exits if critical data (like Sleep Score) is missing, triggering a retry later.
- **Automated**: Runs daily at **06:00 Oslo Time** via GitHub Actions.
- **Resilient**: Uses a 1-hour retry buffer (up to 3 attempts) to handle sync delays.

## Prerequisites

### 1. Garmin Connect
You need a valid Garmin Connect email and password.
*Note: This script works best with accounts that do **not** have MFA enabled for the automated workflow.*

### 2. Google Sheets & Service Account
To allow the script to write to your Google Sheet without manual authentication, you need a **Service Account**.

1.  **Create Project**: Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2.  **Enable API**: Search for "Google Sheets API" and enable it for your project.
3.  **Create Service Account**:
    - Go to **IAM & Admin** > **Service Accounts**.
    - Create a new Service Account.
    - Create a new **Key** (JSON format) and download the file. **Keep this secure!**
4.  **Share Sheet**:
    - Open your target Google Sheet.
    - Click **Share**.
    - Paste the **email address** of the Service Account (found in the JSON file, e.g., `my-app@project-id.iam.gserviceaccount.com`).
    - Grant **Editor** access.

## Setup

### Local Development

1.  **Clone the repository** and navigate to the directory.
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure Environment**:
    - Copy `.env.example` to `.env`.
    - Fill in your details.
    - For `GOOGLE_SERVICE_ACCOUNT_JSON`, paste the **entire content** of the JSON key file you downloaded.

### GitHub Actions (Automation)

To run this automatically, add the following **Secrets** to your GitHub repository (Settings > Secrets and variables > Actions):

- `GARMIN_EMAIL`
- `GARMIN_PASSWORD`
- `GOOGLE_SHEET_ID`: The ID string found in your Google Sheet URL (e.g., `1BxiMVs0XRA5nFNY7...`).
- `GOOGLE_SERVICE_ACCOUNT_JSON`: The full content of your Service Account JSON key.

## Usage

### Run Manually
```bash
python src/main.py
```

### Automated Schedule
The workflow is configured in `.github/workflows/sync_garmin.yml` to run daily.
- **Schedule**: `0 5 * * *` UTC (06:00 Oslo Time).
- **Retries**: If the script exits (e.g., due to missing sleep data), it will retry up to 3 times, once every hour.
