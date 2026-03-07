"""Plot key health metrics over time on a single graph."""

import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

DB_PATH = Path(__file__).parent.parent / "data" / "oura.db"
OUTPUT_PATH = Path(__file__).parent.parent / "outputs"


def normalize(values, label):
    """Normalize to 0-100 scale using tight min/max to accentuate changes."""
    arr = np.array(values, dtype=float)
    vmin, vmax = np.nanmin(arr), np.nanmax(arr)
    if "HR" in label:
        return 100 - 100 * (arr - vmin) / (vmax - vmin)
    return 100 * (arr - vmin) / (vmax - vmin)


def main():
    OUTPUT_PATH.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    sleep_data = conn.execute("""
        SELECT
            SUBSTR(day,1,7) as month,
            ROUND(AVG(deep_sleep_duration * 100.0 / NULLIF(total_sleep_duration, 0)), 1) as deep_pct,
            ROUND(AVG(lowest_heart_rate),1) as lowest_hr,
            ROUND(AVG(average_hrv),1) as hrv
        FROM sleep
        WHERE lowest_heart_rate IS NOT NULL AND total_sleep_duration > 14400
        GROUP BY 1 ORDER BY 1
    """).fetchall()

    activity_data = conn.execute("""
        SELECT
            SUBSTR(day,1,7) as month,
            ROUND(AVG(active_calories)) as active_cal
        FROM daily_activity
        GROUP BY 1 ORDER BY 1
    """).fetchall()
    conn.close()

    sleep_months = [datetime.strptime(r[0], "%Y-%m") for r in sleep_data]
    deep_pct = [r[1] for r in sleep_data]
    lowest_hr = [r[2] for r in sleep_data]
    hrv = [r[3] for r in sleep_data]

    act_months = [datetime.strptime(r[0], "%Y-%m") for r in activity_data]
    active_cal = [r[1] for r in activity_data]

    # Normalize all to 0-100 scale
    deep_norm = normalize(deep_pct, "Deep Sleep")
    hr_norm = normalize(lowest_hr, "Lowest HR")
    hrv_norm = normalize(hrv, "HRV")
    cal_norm = normalize(active_cal, "Active Cal")

    # Plot
    fig, ax = plt.subplots(figsize=(16, 7))
    fig.suptitle("Oura Health Trends (Normalized, Monthly Averages)", fontsize=16, fontweight='bold')

    ax.plot(sleep_months, deep_norm, color='#5B8FB9', linewidth=2.5,
            label=f'Deep Sleep % ({min(deep_pct):.0f}–{max(deep_pct):.0f}%)')
    ax.plot(sleep_months, hr_norm, color='#E74C3C', linewidth=2.5,
            label=f'Lowest HR ({min(lowest_hr):.0f}–{max(lowest_hr):.0f} bpm, inverted)')
    ax.plot(sleep_months, hrv_norm, color='#2ECC71', linewidth=2.5,
            label=f'HRV ({min(hrv):.0f}–{max(hrv):.0f} ms)')
    ax.plot(act_months, cal_norm, color='#F39C12', linewidth=2.5,
            label=f'Active Calories ({min(active_cal):.0f}–{max(active_cal):.0f}/day)')

    # Key events
    new_ring = datetime(2025, 1, 12)
    sober = datetime(2026, 1, 1)
    ax.axvline(new_ring, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.axvline(sober, color='purple', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.text(new_ring, 103, 'new ring', fontsize=9, color='gray', ha='center')
    ax.text(sober, 103, 'no alcohol', fontsize=9, color='purple', ha='center')

    ax.set_ylabel("Relative Scale (higher = better)", fontsize=12, fontweight='bold')
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylim(-5, 110)
    ax.legend(loc='lower left', fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)

    plt.tight_layout()
    out = OUTPUT_PATH / "health_trends.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
