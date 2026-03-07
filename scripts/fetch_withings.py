"""Fetch Withings scale data and store in SQLite."""

import hashlib
import hmac
import json
import sqlite3
import time
from datetime import datetime, date
from pathlib import Path

import requests

DB_PATH = Path(__file__).parent.parent / "data" / "oura.db"
TOKEN_PATH = Path(__file__).parent.parent / "data" / "withings_tokens.json"
ENV_PATH = Path(__file__).parent.parent / ".env"
API_URL = "https://wbsapi.withings.net"
TOKEN_URL = f"{API_URL}/v2/oauth2"

# Withings measure types
MEASURE_TYPES = {
    1: "weight_kg",
    5: "fat_free_mass_kg",
    6: "fat_ratio_pct",
    8: "fat_mass_kg",
    76: "muscle_mass_kg",
    77: "hydration_kg",
    88: "bone_mass_kg",
    91: "pulse_wave_velocity",
}


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
        raise ValueError("No Withings tokens found. Run auth_withings.py first.")

    tokens = json.loads(TOKEN_PATH.read_text())
    access_token = tokens.get("access_token")

    # Test if token is still valid (Withings tokens last 3 hours)
    resp = requests.post(f"{API_URL}/measure", data={
        "action": "getmeas",
        "meastype": 1,
        "category": 1,
        "lastupdate": int(time.time()),
    }, headers={"Authorization": f"Bearer {access_token}"})

    result = resp.json()
    if result.get("status") == 401:
        print("Access token expired, refreshing...")
        access_token = refresh_token(tokens)

    return access_token


def get_nonce(client_id, client_secret):
    """Fetch a fresh nonce from Withings API."""
    timestamp = str(int(time.time()))
    msg = f"getnonce,{client_id},{timestamp}"
    signature = hmac.new(client_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    resp = requests.post(f"{API_URL}/v2/signature", data={
        "action": "getnonce",
        "client_id": client_id,
        "timestamp": timestamp,
        "signature": signature,
    })
    resp.raise_for_status()
    result = resp.json()
    if result.get("status") != 0:
        raise ValueError(f"Failed to get nonce: {result}")
    return result["body"]["nonce"]


def refresh_token(tokens):
    env = load_env()
    client_id = env["WITHINGS_CLIENT_ID"]
    client_secret = env["WITHINGS_CLIENT_SECRET"]

    nonce = get_nonce(client_id, client_secret)
    action = "requesttoken"
    signature = hmac.new(
        client_secret.encode(),
        f"{action},{client_id},{nonce}".encode(),
        hashlib.sha256
    ).hexdigest()

    resp = requests.post(TOKEN_URL, data={
        "action": action,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "nonce": nonce,
        "signature": signature,
    })
    resp.raise_for_status()
    result = resp.json()

    if result.get("status") != 0:
        raise ValueError(f"Token refresh failed: {result}")

    new_tokens = result["body"]
    TOKEN_PATH.write_text(json.dumps(new_tokens, indent=2))
    print("Token refreshed successfully.")
    return new_tokens["access_token"]


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weight (
            date TEXT PRIMARY KEY,
            weight_kg REAL,
            fat_ratio_pct REAL,
            fat_mass_kg REAL,
            fat_free_mass_kg REAL,
            muscle_mass_kg REAL,
            bone_mass_kg REAL,
            hydration_kg REAL
        )
    """)


def fetch_weight(token):
    """Fetch all weight measurements."""
    # Fetch from beginning of time
    resp = requests.post(f"{API_URL}/measure", data={
        "action": "getmeas",
        "category": 1,  # real measurements only (not goals)
        "startdate": 0,
        "enddate": int(time.time()),
    }, headers={"Authorization": f"Bearer {token}"})

    resp.raise_for_status()
    result = resp.json()

    if result.get("status") != 0:
        print(f"API error: {result}")
        return []

    # Parse measurement groups
    measurements = {}  # date -> {field: value}

    for grp in result.get("body", {}).get("measuregrps", []):
        dt = datetime.fromtimestamp(grp["date"]).strftime("%Y-%m-%d")

        if dt not in measurements:
            measurements[dt] = {}

        for measure in grp.get("measures", []):
            mtype = measure["type"]
            # Value is stored as value * 10^unit
            value = measure["value"] * (10 ** measure["unit"])

            field = MEASURE_TYPES.get(mtype)
            if field:
                measurements[dt][field] = round(value, 2)

    return measurements


def main():
    token = get_token()
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    print("Fetching Withings data...")
    measurements = fetch_weight(token)

    count = 0
    for day, data in measurements.items():
        conn.execute("""
            INSERT OR REPLACE INTO weight (date, weight_kg, fat_ratio_pct, fat_mass_kg,
                fat_free_mass_kg, muscle_mass_kg, bone_mass_kg, hydration_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            day,
            data.get("weight_kg"),
            data.get("fat_ratio_pct"),
            data.get("fat_mass_kg"),
            data.get("fat_free_mass_kg"),
            data.get("muscle_mass_kg"),
            data.get("bone_mass_kg"),
            data.get("hydration_kg"),
        ])
        count += 1

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM weight").fetchone()[0]
    date_range = conn.execute("SELECT MIN(date), MAX(date) FROM weight").fetchone()
    conn.close()

    print(f"  Stored {count} measurements")
    print(f"  Total: {total} days, {date_range[0]} to {date_range[1]}")
    print("Done!")


if __name__ == "__main__":
    main()
