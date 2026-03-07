"""Fetch Oura Ring data and store in SQLite."""

import json
import sqlite3
import requests
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "oura.db"
TOKEN_PATH = Path(__file__).parent.parent / "data" / "tokens.json"
ENV_PATH = Path(__file__).parent.parent / ".env"
BASE_URL = "https://api.ouraring.com/v2/usercollection"
TOKEN_URL = "https://api.ouraring.com/oauth/token"


def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_token():
    if not TOKEN_PATH.exists():
        raise ValueError("No tokens found. Run auth_oura.py first.")

    tokens = json.loads(TOKEN_PATH.read_text())
    access_token = tokens.get("access_token")

    # Test if token is still valid
    resp = requests.get(
        f"{BASE_URL}/personal_info",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if resp.status_code == 401:
        # Token expired, try refresh
        print("Access token expired, refreshing...")
        access_token = refresh_token(tokens)

    return access_token


def refresh_token(tokens):
    env = load_env()
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": env["OURA_CLIENT_ID"],
        "client_secret": env["OURA_CLIENT_SECRET"],
    })
    resp.raise_for_status()
    new_tokens = resp.json()
    TOKEN_PATH.write_text(json.dumps(new_tokens, indent=2))
    print("Token refreshed successfully.")
    return new_tokens["access_token"]


def get_headers(token):
    return {"Authorization": f"Bearer {token}"}


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sleep (
            id TEXT PRIMARY KEY,
            day TEXT,
            bedtime_start TEXT,
            bedtime_end TEXT,
            duration INTEGER,
            total_sleep_duration INTEGER,
            awake_time INTEGER,
            light_sleep_duration INTEGER,
            deep_sleep_duration INTEGER,
            rem_sleep_duration INTEGER,
            restless_periods INTEGER,
            average_breath REAL,
            average_heart_rate REAL,
            lowest_heart_rate INTEGER,
            average_hrv REAL,
            temperature_delta REAL,
            score INTEGER,
            efficiency INTEGER,
            latency INTEGER
        );

        CREATE TABLE IF NOT EXISTS daily_readiness (
            id TEXT PRIMARY KEY,
            day TEXT UNIQUE,
            score INTEGER,
            temperature_deviation REAL,
            activity_balance INTEGER,
            body_temperature INTEGER,
            hrv_balance INTEGER,
            previous_day_activity INTEGER,
            previous_night INTEGER,
            recovery_index INTEGER,
            resting_heart_rate INTEGER,
            sleep_balance INTEGER
        );

        CREATE TABLE IF NOT EXISTS daily_activity (
            id TEXT PRIMARY KEY,
            day TEXT UNIQUE,
            score INTEGER,
            active_calories INTEGER,
            total_calories INTEGER,
            steps INTEGER,
            equivalent_walking_distance INTEGER,
            high_activity_time INTEGER,
            medium_activity_time INTEGER,
            low_activity_time INTEGER,
            sedentary_time INTEGER,
            resting_time INTEGER
        );

        CREATE TABLE IF NOT EXISTS heart_rate (
            timestamp TEXT PRIMARY KEY,
            bpm INTEGER,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_spo2 (
            id TEXT PRIMARY KEY,
            day TEXT UNIQUE,
            spo2_average REAL,
            breathing_disturbance_index INTEGER
        );
    """)


def get_last_date(conn, table, date_col="day"):
    row = conn.execute(f"SELECT MAX({date_col}) FROM {table}").fetchone()
    if row[0]:
        return date.fromisoformat(row[0][:10]) + timedelta(days=1)
    return date(2015, 1, 1)  # default: fetch all available history


def fetch_and_store(conn, token, endpoint, table, parse_fn, date_col="day"):
    start = get_last_date(conn, table, date_col)
    end = date.today() + timedelta(days=1)
    if start >= end:
        print(f"  {table}: already up to date")
        return 0

    print(f"  {table}: fetching {start} to {end}")
    url = f"{BASE_URL}/{endpoint}"
    params = {"start_date": str(start), "end_date": str(end)}

    count = 0
    while url:
        resp = requests.get(url, headers=get_headers(token), params=params)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("data", []):
            try:
                row = parse_fn(item)
                placeholders = ",".join(["?"] * len(row))
                cols = ",".join(row.keys())
                conn.execute(
                    f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})",
                    list(row.values())
                )
                count += 1
            except (KeyError, TypeError) as e:
                print(f"    skipping record: {e}")

        conn.commit()
        url = data.get("next_token")
        if url:
            params = {"next_token": url}
            url = f"{BASE_URL}/{endpoint}"
        else:
            url = None

    print(f"  {table}: stored {count} records")
    return count


def parse_sleep(item):
    return {
        "id": item["id"],
        "day": item.get("day"),
        "bedtime_start": item.get("bedtime_start"),
        "bedtime_end": item.get("bedtime_end"),
        "duration": item.get("duration"),
        "total_sleep_duration": item.get("total_sleep_duration"),
        "awake_time": item.get("awake_time"),
        "light_sleep_duration": item.get("light_sleep_duration"),
        "deep_sleep_duration": item.get("deep_sleep_duration"),
        "rem_sleep_duration": item.get("rem_sleep_duration"),
        "restless_periods": item.get("restless_periods"),
        "average_breath": item.get("average_breath"),
        "average_heart_rate": item.get("average_heart_rate"),
        "lowest_heart_rate": item.get("lowest_heart_rate"),
        "average_hrv": item.get("average_hrv"),
        "temperature_delta": item.get("temperature_delta"),
        "score": item.get("score"),
        "efficiency": item.get("efficiency"),
        "latency": item.get("latency"),
    }


def parse_readiness(item):
    contributors = item.get("contributors", {})
    return {
        "id": item["id"],
        "day": item.get("day"),
        "score": item.get("score"),
        "temperature_deviation": item.get("temperature_deviation"),
        "activity_balance": contributors.get("activity_balance"),
        "body_temperature": contributors.get("body_temperature"),
        "hrv_balance": contributors.get("hrv_balance"),
        "previous_day_activity": contributors.get("previous_day_activity"),
        "previous_night": contributors.get("previous_night"),
        "recovery_index": contributors.get("recovery_index"),
        "resting_heart_rate": contributors.get("resting_heart_rate"),
        "sleep_balance": contributors.get("sleep_balance"),
    }


def parse_activity(item):
    return {
        "id": item["id"],
        "day": item.get("day"),
        "score": item.get("score"),
        "active_calories": item.get("active_calories"),
        "total_calories": item.get("total_calories"),
        "steps": item.get("steps"),
        "equivalent_walking_distance": item.get("equivalent_walking_distance"),
        "high_activity_time": item.get("high_activity_time"),
        "medium_activity_time": item.get("medium_activity_time"),
        "low_activity_time": item.get("low_activity_time"),
        "sedentary_time": item.get("sedentary_time"),
        "resting_time": item.get("resting_time"),
    }


def parse_heart_rate(item):
    return {
        "timestamp": item["timestamp"],
        "bpm": item.get("bpm"),
        "source": item.get("source"),
    }


def parse_spo2(item):
    spo2_pct = item.get("spo2_percentage") or {}
    return {
        "id": item["id"],
        "day": item.get("day"),
        "spo2_average": spo2_pct.get("average") if isinstance(spo2_pct, dict) else None,
        "breathing_disturbance_index": item.get("breathing_disturbance_index"),
    }


def main():
    token = get_token()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    endpoints = [
        ("sleep", "sleep", parse_sleep, "day"),
        ("daily_readiness", "daily_readiness", parse_readiness, "day"),
        ("daily_activity", "daily_activity", parse_activity, "day"),
        ("heartrate", "heart_rate", parse_heart_rate, "timestamp"),
        ("daily_spo2", "daily_spo2", parse_spo2, "day"),
    ]

    print("Fetching Oura data...")
    for endpoint, table, parse_fn, date_col in endpoints:
        try:
            fetch_and_store(conn, token, endpoint, table, parse_fn, date_col=date_col)
        except Exception as e:
            print(f"  {table}: ERROR - {e}")

    # Summary
    for table in ["sleep", "daily_readiness", "daily_activity", "heart_rate", "daily_spo2"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} total records")

    conn.close()
    print("Done!")


if __name__ == "__main__":
    main()
