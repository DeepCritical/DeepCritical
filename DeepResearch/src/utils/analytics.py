# ─── analytics.py ──────────────────────────────────────────────────────────────
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from filelock import FileLock  # pip install filelock
import pandas as pd  # already available in HF images

# Determine data directory based on environment
# 1. Check for environment variable override
# 2. Use /data if it exists and is writable (Hugging Face Spaces with persistent storage)
# 3. Use ./data for local development
DATA_DIR = os.getenv("ANALYTICS_DATA_DIR")
if not DATA_DIR:
    if os.path.exists("/data") and os.access("/data", os.W_OK):
        DATA_DIR = "/data"
        print("[Analytics] Using persistent storage at /data")
    else:
        DATA_DIR = "./data"
        print("[Analytics] Using local storage at ./data")

os.makedirs(DATA_DIR, exist_ok=True)

COUNTS_FILE = os.path.join(DATA_DIR, "request_counts.json")
TIMES_FILE = os.path.join(DATA_DIR, "request_times.json")
LOCK_FILE = os.path.join(DATA_DIR, "analytics.lock")


class AnalyticsEngine:
    """Main analytics engine for tracking request metrics."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize analytics engine."""
        self.data_dir = data_dir or DATA_DIR
        self.counts_file = os.path.join(self.data_dir, "request_counts.json")
        self.times_file = os.path.join(self.data_dir, "request_times.json")
        self.lock_file = os.path.join(self.data_dir, "analytics.lock")

    def record_request(self, endpoint: str, status_code: int, duration: float):
        """Record a request for analytics."""
        return record_request(duration, status_code)

    def get_last_n_days_df(self, days: int):
        """Get analytics data for last N days."""
        return last_n_days_df(days)

    def get_avg_time_df(self, days: int):
        """Get average time analytics."""
        return last_n_days_avg_time_df(days)


def _load() -> dict:
    if not os.path.exists(COUNTS_FILE):
        return {}
    with open(COUNTS_FILE) as f:
        return json.load(f)


def _save(data: dict):
    with open(COUNTS_FILE, "w") as f:
        json.dump(data, f)


def _load_times() -> dict:
    if not os.path.exists(TIMES_FILE):
        return {}
    with open(TIMES_FILE) as f:
        return json.load(f)


def _save_times(data: dict):
    with open(TIMES_FILE, "w") as f:
        json.dump(data, f)


async def record_request(
    duration: Optional[float] = None, num_results: Optional[int] = None
) -> None:
    """Increment today's counter (UTC) atomically and optionally record request duration."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with FileLock(LOCK_FILE):
        # Update counts
        data = _load()
        data[today] = data.get(today, 0) + 1
        _save(data)

        # Only record times for default requests (num_results=4)
        if duration is not None and (num_results is None or num_results == 4):
            times = _load_times()
            if today not in times:
                times[today] = []
            times[today].append(round(duration, 2))
            _save_times(times)


def last_n_days_df(n: int = 30) -> pd.DataFrame:
    """Return a DataFrame with a row for each of the past *n* days."""
    now = datetime.now(timezone.utc)
    with FileLock(LOCK_FILE):
        data = _load()
    records = []
    for i in range(n):
        day = now - timedelta(days=n - 1 - i)
        day_str = day.strftime("%Y-%m-%d")
        # Format date for display (MMM DD)
        display_date = day.strftime("%b %d")
        records.append(
            {
                "date": display_date,
                "count": data.get(day_str, 0),
                "full_date": day_str,  # Keep full date for tooltip
            }
        )
    return pd.DataFrame(records)


def last_n_days_avg_time_df(n: int = 30) -> pd.DataFrame:
    """Return a DataFrame with average request time for each of the past *n* days."""
    now = datetime.now(timezone.utc)
    with FileLock(LOCK_FILE):
        times = _load_times()
    records = []
    for i in range(n):
        day = now - timedelta(days=n - 1 - i)
        day_str = day.strftime("%Y-%m-%d")
        # Format date for display (MMM DD)
        display_date = day.strftime("%b %d")

        # Calculate average time for the day
        day_times = times.get(day_str, [])
        avg_time = round(sum(day_times) / len(day_times), 2) if day_times else 0

        records.append(
            {
                "date": display_date,
                "avg_time": avg_time,
                "request_count": len(day_times),
                "full_date": day_str,  # Keep full date for tooltip
            }
        )
    return pd.DataFrame(records)


class MetricCalculator:
    """Calculator for various analytics metrics."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize metric calculator."""
        self.data_dir = data_dir or DATA_DIR

    def calculate_request_rate(self, days: int = 7) -> float:
        """Calculate average requests per day."""
        df = last_n_days_df(days)
        if df.empty:
            return 0.0
        return df["request_count"].sum() / days

    def calculate_avg_response_time(self, days: int = 7) -> float:
        """Calculate average response time."""
        df = last_n_days_avg_time_df(days)
        if df.empty:
            return 0.0
        return df["avg_time"].mean()

    def calculate_success_rate(self, days: int = 7) -> float:
        """Calculate success rate percentage."""
        df = last_n_days_df(days)
        if df.empty:
            return 0.0
        # For now, assume all requests are successful
        # In a real implementation, this would check actual status codes
        return 100.0
