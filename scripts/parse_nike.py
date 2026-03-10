"""Parse Nike TCX files and store run summaries in SQLite."""

import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "oura.db"
TCX_DIR = Path(__file__).parent.parent / "data" / "nikeuserdata" / "tcx"

NS = {
    "tc": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ns3": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
}


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            date TEXT,
            sport TEXT,
            duration_sec REAL,
            distance_m REAL,
            distance_km REAL,
            calories INTEGER,
            avg_speed_mps REAL,
            max_speed_mps REAL,
            pace_min_per_km REAL,
            avg_hr INTEGER,
            max_hr INTEGER,
            elevation_gain_m REAL,
            has_gps INTEGER,
            has_hr INTEGER,
            trackpoint_count INTEGER
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_date ON runs(date)
    """)


def parse_tcx(filepath):
    """Parse a TCX file and return summary dict."""
    try:
        tree = ET.parse(filepath)
    except ET.ParseError:
        return None

    root = tree.getroot()
    activity = root.find(".//tc:Activity", NS)
    if activity is None:
        return None

    sport = activity.get("Sport", "Unknown")
    activity_id = activity.findtext("tc:Id", "", NS).strip()

    # Aggregate across all laps
    total_time = 0
    total_dist = 0
    total_cal = 0
    max_speed = 0
    heart_rates = []
    max_hr = 0
    trackpoint_count = 0
    has_gps = False
    has_hr = False
    elevations = []

    for lap in activity.findall("tc:Lap", NS):
        t = lap.findtext("tc:TotalTimeSeconds", "0", NS)
        total_time += float(t)

        d = lap.findtext("tc:DistanceMeters", "0", NS)
        total_dist += float(d)

        c = lap.findtext("tc:Calories", "0", NS)
        total_cal += int(float(c))

        ms = lap.findtext("tc:MaximumSpeed", "0", NS)
        max_speed = max(max_speed, float(ms))

        # Scan trackpoints for HR, GPS, elevation
        for tp in lap.findall(".//tc:Trackpoint", NS):
            trackpoint_count += 1

            pos = tp.find("tc:Position", NS)
            if pos is not None:
                has_gps = True

            alt = tp.findtext("tc:AltitudeMeters", None, NS)
            if alt is not None:
                elevations.append(float(alt))

            hr_elem = tp.find("tc:HeartRateBpm", NS)
            if hr_elem is not None:
                hr_val = hr_elem.findtext("tc:Value", "0", NS)
                hr = int(float(hr_val))
                if hr > 0:
                    heart_rates.append(hr)
                    max_hr = max(max_hr, hr)
                    has_hr = True

    if total_time == 0:
        return None

    # Calculate derived metrics
    avg_speed = total_dist / total_time if total_time > 0 else 0
    distance_km = total_dist / 1000
    pace = (total_time / 60) / distance_km if distance_km > 0 else 0
    avg_hr = sum(heart_rates) // len(heart_rates) if heart_rates else None

    # Elevation gain
    elevation_gain = 0
    for i in range(1, len(elevations)):
        diff = elevations[i] - elevations[i - 1]
        if diff > 0:
            elevation_gain += diff

    # Parse date from activity ID
    try:
        dt = datetime.fromisoformat(activity_id.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        date_str = None

    return {
        "id": filepath.stem,
        "date": date_str,
        "sport": sport,
        "duration_sec": round(total_time, 1),
        "distance_m": round(total_dist, 1),
        "distance_km": round(distance_km, 2),
        "calories": total_cal,
        "avg_speed_mps": round(avg_speed, 3),
        "max_speed_mps": round(max_speed, 3),
        "pace_min_per_km": round(pace, 2),
        "avg_hr": avg_hr,
        "max_hr": max_hr if max_hr > 0 else None,
        "elevation_gain_m": round(elevation_gain, 1),
        "has_gps": int(has_gps),
        "has_hr": int(has_hr),
        "trackpoint_count": trackpoint_count,
    }


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    tcx_files = sorted(TCX_DIR.glob("*.tcx"))
    print(f"Found {len(tcx_files)} TCX files")

    count = 0
    skipped = 0
    for f in tcx_files:
        result = parse_tcx(f)
        if result is None:
            skipped += 1
            continue

        conn.execute("""
            INSERT OR REPLACE INTO runs
            (id, date, sport, duration_sec, distance_m, distance_km, calories,
             avg_speed_mps, max_speed_mps, pace_min_per_km, avg_hr, max_hr,
             elevation_gain_m, has_gps, has_hr, trackpoint_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [result[k] for k in [
            "id", "date", "sport", "duration_sec", "distance_m", "distance_km",
            "calories", "avg_speed_mps", "max_speed_mps", "pace_min_per_km",
            "avg_hr", "max_hr", "elevation_gain_m", "has_gps", "has_hr",
            "trackpoint_count"
        ]])
        count += 1

    conn.commit()

    # Summary
    print(f"Parsed {count} activities, skipped {skipped}")
    rows = conn.execute("""
        SELECT sport, COUNT(*), MIN(date), MAX(date),
               ROUND(AVG(distance_km),1), ROUND(AVG(duration_sec/60),1),
               ROUND(AVG(pace_min_per_km),1)
        FROM runs GROUP BY sport ORDER BY COUNT(*) DESC
    """).fetchall()
    print(f"\nBy sport:")
    for r in rows:
        print(f"  {r[0]}: {r[1]} activities, {r[2]} to {r[3]}, avg {r[4]}km in {r[5]}min (pace {r[6]} min/km)")

    # Year breakdown
    print(f"\nBy year:")
    rows = conn.execute("""
        SELECT substr(date,1,4) as yr, COUNT(*), ROUND(SUM(distance_km),1),
               ROUND(AVG(pace_min_per_km),1), ROUND(AVG(distance_km),1)
        FROM runs WHERE date IS NOT NULL GROUP BY yr ORDER BY yr
    """).fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]} runs, {r[2]} total km, avg pace {r[3]} min/km, avg dist {r[4]} km")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
