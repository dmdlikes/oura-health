"""Reusable analysis and visualization helpers for Oura data."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "oura.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def query(sql, params=None):
    """Run a query and return results as list of dicts."""
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(sql, params or [])
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def recent_sleep(days=30):
    return query("""
        SELECT * FROM sleep
        WHERE day >= date('now', ?)
        ORDER BY day DESC
    """, [f"-{days} days"])

def recent_readiness(days=30):
    return query("""
        SELECT * FROM daily_readiness
        WHERE day >= date('now', ?)
        ORDER BY day DESC
    """, [f"-{days} days"])

def recent_activity(days=30):
    return query("""
        SELECT * FROM daily_activity
        WHERE day >= date('now', ?)
        ORDER BY day DESC
    """, [f"-{days} days"])

def sleep_summary(days=30):
    """Average sleep metrics over the last N days."""
    return query("""
        SELECT
            COUNT(*) as nights,
            ROUND(AVG(score), 1) as avg_score,
            ROUND(AVG(total_sleep_duration) / 3600.0, 1) as avg_hours,
            ROUND(AVG(deep_sleep_duration) / 3600.0, 1) as avg_deep_hours,
            ROUND(AVG(rem_sleep_duration) / 3600.0, 1) as avg_rem_hours,
            ROUND(AVG(efficiency), 1) as avg_efficiency,
            ROUND(AVG(average_hrv), 1) as avg_hrv,
            ROUND(AVG(average_heart_rate), 1) as avg_hr,
            ROUND(AVG(lowest_heart_rate), 1) as avg_lowest_hr
        FROM sleep
        WHERE day >= date('now', ?)
    """, [f"-{days} days"])
