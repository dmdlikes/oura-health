"""Plot correlated metric pairs in quadrants."""

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


def normalize(values):
    arr = np.array(values, dtype=float)
    vmin, vmax = np.nanmin(arr), np.nanmax(arr)
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

    # Build aligned activity data (match to sleep months)
    act_dict = {datetime.strptime(r[0], "%Y-%m"): r[1] for r in activity_data}
    active_cal_aligned = [act_dict.get(m) for m in sleep_months]

    new_ring = datetime(2025, 1, 12)
    sober = datetime(2026, 1, 1)

    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    fig.suptitle("Correlated Health Metrics (Monthly Averages)", fontsize=18, fontweight='bold', y=0.98)

    def style_ax(ax):
        ax.grid(True, alpha=0.25)
        ax.axvline(new_ring, color='gray', linestyle='--', alpha=0.35, linewidth=1)
        ax.axvline(sober, color='purple', linestyle='--', alpha=0.35, linewidth=1)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b \'%y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        ax.tick_params(axis='x', rotation=45)

    # --- Q1: HRV & Deep Sleep % ---
    ax = axes[0, 0]
    ax.set_title("HRV & Deep Sleep %", fontsize=13, fontweight='bold')
    ax1 = ax
    ax2 = ax.twinx()
    l1, = ax1.plot(sleep_months, hrv, color='#2ECC71', linewidth=2.5, label='HRV (ms)')
    l2, = ax2.plot(sleep_months, deep_pct, color='#5B8FB9', linewidth=2.5, label='Deep Sleep %', alpha=0.85)
    ax1.set_ylabel("HRV (ms)", color='#2ECC71', fontweight='bold')
    ax2.set_ylabel("Deep Sleep %", color='#5B8FB9', fontweight='bold')
    ax1.tick_params(axis='y', colors='#2ECC71')
    ax2.tick_params(axis='y', colors='#5B8FB9')
    ax.legend([l1, l2], ['HRV (ms)', 'Deep Sleep %'], loc='upper right', fontsize=9)
    style_ax(ax)

    # --- Q2: Active Calories → HRV (leading indicator) ---
    ax = axes[0, 1]
    ax.set_title("Active Calories → HRV (activity leads)", fontsize=13, fontweight='bold')
    ax1 = ax
    ax2 = ax.twinx()
    l1, = ax1.plot(act_months, active_cal, color='#F39C12', linewidth=2.5, label='Active Cal')
    l2, = ax2.plot(sleep_months, hrv, color='#2ECC71', linewidth=2.5, label='HRV (ms)', alpha=0.85)
    ax1.set_ylabel("Active Calories", color='#F39C12', fontweight='bold')
    ax2.set_ylabel("HRV (ms)", color='#2ECC71', fontweight='bold')
    ax1.tick_params(axis='y', colors='#F39C12')
    ax2.tick_params(axis='y', colors='#2ECC71')
    ax.legend([l1, l2], ['Active Calories', 'HRV (ms)'], loc='upper right', fontsize=9)
    style_ax(ax)

    # --- Q3: Active Calories → Lowest HR ---
    ax = axes[1, 0]
    ax.set_title("Active Calories → Lowest HR", fontsize=13, fontweight='bold')
    ax1 = ax
    ax2 = ax.twinx()
    l1, = ax1.plot(act_months, active_cal, color='#F39C12', linewidth=2.5, label='Active Cal')
    l2, = ax2.plot(sleep_months, lowest_hr, color='#E74C3C', linewidth=2.5, label='Lowest HR (bpm)', alpha=0.85)
    ax2.invert_yaxis()
    ax1.set_ylabel("Active Calories", color='#F39C12', fontweight='bold')
    ax2.set_ylabel("Lowest HR (bpm, inverted)", color='#E74C3C', fontweight='bold')
    ax1.tick_params(axis='y', colors='#F39C12')
    ax2.tick_params(axis='y', colors='#E74C3C')
    ax.legend([l1, l2], ['Active Calories', 'Lowest HR (inverted)'], loc='upper right', fontsize=9)
    style_ax(ax)

    # --- Q4: HRV → Lowest HR ---
    ax = axes[1, 1]
    ax.set_title("HRV → Lowest HR (HRV predicts HR)", fontsize=13, fontweight='bold')
    ax1 = ax
    ax2 = ax.twinx()
    l1, = ax1.plot(sleep_months, hrv, color='#2ECC71', linewidth=2.5, label='HRV (ms)')
    l2, = ax2.plot(sleep_months, lowest_hr, color='#E74C3C', linewidth=2.5, label='Lowest HR (bpm)', alpha=0.85)
    ax2.invert_yaxis()
    ax1.set_ylabel("HRV (ms)", color='#2ECC71', fontweight='bold')
    ax2.set_ylabel("Lowest HR (bpm, inverted)", color='#E74C3C', fontweight='bold')
    ax1.tick_params(axis='y', colors='#2ECC71')
    ax2.tick_params(axis='y', colors='#E74C3C')
    ax.legend([l1, l2], ['HRV (ms)', 'Lowest HR (inverted)'], loc='upper right', fontsize=9)
    style_ax(ax)

    plt.tight_layout()
    out = OUTPUT_PATH / "correlations.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
