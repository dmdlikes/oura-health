"""Generate health dashboard as self-contained HTML."""

import base64
import hashlib
import json
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

DB_PATH = Path(__file__).parent.parent / "data" / "oura.db"
OUT_PATH = Path(__file__).parent.parent / "outputs" / "dashboard.html"
ENCRYPTED_PATH = Path(__file__).parent.parent / "docs" / "index.html"
TOKEN_FILE = Path(__file__).parent.parent / "data" / "log_token.txt"
PASSWORD_FILE = Path(__file__).parent.parent / "data" / "dashboard_password.txt"

# Targets
TARGET_HR = 57
TARGET_WEIGHT = 80
TARGET_BDI = 4.0
TARGET_STEPS = 9500
STEP_STREAK_THRESHOLD = 9000
SLEEP_FLOOR = 6.0

# Colors
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"
BLUE = "#3b82f6"
PURPLE = "#a855f7"
ORANGE = "#f97316"
GRAY = "#6b7280"
LIGHT_GRAY = "#e5e7eb"
BG = "#0f172a"
CARD_BG = "#1e293b"
TEXT = "#f1f5f9"
SUBTEXT = "#94a3b8"


def query(conn, sql, params=None):
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params or []).fetchall()
    return [dict(r) for r in rows]


def get_data(conn, days=90):
    start = str(date.today() - timedelta(days=days))
    start_long = str(date.today() - timedelta(days=days + 30))  # extra for rolling avgs

    # Ensure optional tables exist
    conn.execute("CREATE TABLE IF NOT EXISTS daily_tags (day TEXT PRIMARY KEY, mouth_tape INTEGER DEFAULT 0, notes TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS labs (date TEXT, test TEXT, value REAL, unit TEXT, flag TEXT, reference TEXT, PRIMARY KEY (date, test))")
    conn.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, date TEXT, sport TEXT, duration_sec REAL, distance_m REAL, distance_km REAL, calories INTEGER, avg_speed_mps REAL, max_speed_mps REAL, pace_min_per_km REAL, avg_hr INTEGER, max_hr INTEGER, elevation_gain_m REAL, has_gps INTEGER, has_hr INTEGER, trackpoint_count INTEGER)")

    sleep = query(conn, """
        SELECT day, total_sleep_duration/3600.0 as sleep_hrs,
            lowest_heart_rate as hr, average_hrv as hrv,
            deep_sleep_duration/3600.0 as deep_hrs,
            total_sleep_duration/3600.0 as total_hrs,
            efficiency, bedtime_start, score as sleep_score
        FROM sleep WHERE day >= ? ORDER BY day
    """, [start_long])

    activity = query(conn, """
        SELECT day, steps, active_calories as cal,
            high_activity_time/60.0 as high_min,
            medium_activity_time/60.0 as med_min,
            low_activity_time/60.0 as low_min
        FROM daily_activity WHERE day >= ? ORDER BY day
    """, [start_long])

    spo2 = query(conn, """
        SELECT day, spo2_average as spo2, breathing_disturbance_index as bdi
        FROM daily_spo2 WHERE day >= ? AND breathing_disturbance_index IS NOT NULL
        ORDER BY day
    """, [start_long])

    weight = query(conn, """
        SELECT date as day, weight_kg, fat_ratio_pct, fat_mass_kg, fat_free_mass_kg
        FROM weight WHERE date >= ? AND weight_kg IS NOT NULL ORDER BY date
    """, [start_long])

    tags = query(conn, """
        SELECT day, mouth_tape, notes FROM daily_tags WHERE day >= ? ORDER BY day
    """, [start_long])

    # Labs - all time (not filtered by date range)
    labs = query(conn, """
        SELECT date, test, value, unit, flag FROM labs
        WHERE test IN ('total_cholesterol','ldl','hdl','triglycerides','apob','hba1c','glucose','crp')
        ORDER BY date
    """)

    # Runs - all time for long-term chart
    runs = query(conn, """
        SELECT date, distance_km, duration_sec, pace_min_per_km, calories, avg_hr
        FROM runs WHERE date IS NOT NULL ORDER BY date
    """)

    return sleep, activity, spo2, weight, tags, labs, runs


def rolling_avg(values, window=7):
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = [v for v in values[start:i+1] if v is not None]
        result.append(sum(chunk) / len(chunk) if chunk else None)
    return result


def score_color(current, target, lower_is_better=True):
    if current is None:
        return GRAY
    if lower_is_better:
        ratio = target / current if current != 0 else 1
    else:
        ratio = current / target if target != 0 else 1
    if ratio >= 0.95:
        return GREEN
    elif ratio >= 0.85:
        return YELLOW
    return RED


def trend_arrow(values, window=14):
    recent = [v for v in values[-window:] if v is not None]
    older = [v for v in values[-window*2:-window] if v is not None]
    if not recent or not older:
        return "→", SUBTEXT
    diff = sum(recent)/len(recent) - sum(older)/len(older)
    if abs(diff) < 0.5:
        return "→", SUBTEXT
    return ("↓" if diff < 0 else "↑"), (GREEN if diff < 0 else RED)


def get_local_ip():
    """Get LAN IP for the log server URLs."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def build_dashboard():
    log_token = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else ""
    local_ip = get_local_ip()
    server_base = f"http://{local_ip}:8097"
    conn = sqlite3.connect(DB_PATH)
    sleep, activity, spo2, weight, tags, labs, runs = get_data(conn, days=90)

    # Build lookup dicts
    sleep_by_day = {r["day"]: r for r in sleep}
    act_by_day = {r["day"]: r for r in activity}
    spo2_by_day = {r["day"]: r for r in spo2}
    weight_by_day = {r["day"]: r for r in weight}
    tags_by_day = {r["day"]: r for r in tags}

    # Date range for display
    end_date = date.today()
    start_date = end_date - timedelta(days=90)
    all_days = [str(start_date + timedelta(days=i)) for i in range(91)]

    # --- Compute scorecard values ---
    recent_7 = all_days[-7:]
    recent_hrs = [sleep_by_day[d]["hr"] for d in recent_7 if d in sleep_by_day and sleep_by_day[d]["hr"]]
    recent_steps = [act_by_day[d]["steps"] for d in recent_7 if d in act_by_day and act_by_day[d]["steps"]]
    recent_bdi = [spo2_by_day[d]["bdi"] for d in recent_7 if d in spo2_by_day and spo2_by_day[d]["bdi"]]

    # Latest weight (use most recent weigh-in)
    recent_weights = [weight_by_day[d]["weight_kg"] for d in reversed(all_days) if d in weight_by_day]

    avg_hr = sum(recent_hrs) / len(recent_hrs) if recent_hrs else None
    avg_steps = sum(recent_steps) / len(recent_steps) if recent_steps else None
    avg_bdi = sum(recent_bdi) / len(recent_bdi) if recent_bdi else None
    curr_weight = recent_weights[0] if recent_weights else None

    # Step streak (skip today since it's incomplete)
    streak = 0
    streak_days = [d for d in all_days if d < str(date.today())]
    for d in reversed(streak_days):
        if d in act_by_day and act_by_day[d]["steps"] and act_by_day[d]["steps"] >= STEP_STREAK_THRESHOLD:
            streak += 1
        else:
            break

    # Weekly cal load
    last_7_cal = [act_by_day[d]["cal"] for d in recent_7 if d in act_by_day and act_by_day[d]["cal"]]
    weekly_cal = sum(last_7_cal) if last_7_cal else 0

    # --- Build time series ---
    hr_series = [sleep_by_day.get(d, {}).get("hr") for d in all_days]
    hrv_series = [sleep_by_day.get(d, {}).get("hrv") for d in all_days]
    step_series = [act_by_day.get(d, {}).get("steps") for d in all_days]
    sleep_hrs_series = [sleep_by_day.get(d, {}).get("sleep_hrs") for d in all_days]
    deep_series = [sleep_by_day.get(d, {}).get("deep_hrs") for d in all_days]
    bdi_series = [spo2_by_day.get(d, {}).get("bdi") for d in all_days]
    spo2_series = [spo2_by_day.get(d, {}).get("spo2") for d in all_days]
    cal_series = [act_by_day.get(d, {}).get("cal") for d in all_days]

    wt_days = [d for d in all_days if d in weight_by_day]
    wt_vals = [weight_by_day[d]["weight_kg"] for d in wt_days]
    fat_vals = [weight_by_day[d].get("fat_ratio_pct") for d in wt_days]
    ffm_vals = [weight_by_day[d].get("fat_free_mass_kg") for d in wt_days]
    fm_vals = [weight_by_day[d].get("fat_mass_kg") for d in wt_days]

    hr_roll = rolling_avg(hr_series)
    hrv_roll = rolling_avg(hrv_series)
    step_roll = rolling_avg(step_series)
    bdi_roll = rolling_avg(bdi_series)
    wt_roll = rolling_avg(wt_vals, window=14)

    # --- Normalize for quad trend ---
    def normalize(vals, invert=False):
        clean = [v for v in vals if v is not None]
        if not clean:
            return [None] * len(vals)
        mn, mx = min(clean), max(clean)
        rng = mx - mn if mx != mn else 1
        result = []
        for v in vals:
            if v is None:
                result.append(None)
            else:
                n = (v - mn) / rng * 100
                result.append(100 - n if invert else n)
        return result

    # --- HR trend arrow ---
    hr_arrow, hr_arrow_color = trend_arrow(hr_series)
    step_arrow, step_arrow_color = trend_arrow(step_series)

    # =========================================================
    # BUILD THE HTML
    # =========================================================

    # --- Row 3 Left: Stacked Trend Charts ---
    def tight_range(vals, pad_pct=0.15, target=None):
        clean = [v for v in vals if v is not None]
        if not clean:
            return [0, 100]
        mn, mx = min(clean), max(clean)
        if target is not None:
            mn = min(mn, target)
            mx = max(mx, target)
        pad = (mx - mn) * pad_pct
        return [mn - pad, mx + pad]

    trend_metrics = [
        ("Lowest HR (bpm)", hr_roll, RED, TARGET_HR, "HR: %{y:.1f} bpm"),
        ("HRV (ms)", hrv_roll, BLUE, None, "HRV: %{y:.1f} ms"),
        ("Steps", step_roll, GREEN, TARGET_STEPS, "Steps: %{y:,.0f}"),
        ("BDI", bdi_roll, ORANGE, TARGET_BDI, "BDI: %{y:.1f}"),
    ]

    fig_trend = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
        row_heights=[1, 1, 1, 1],
    )
    for i, (label, vals, color, target, hover) in enumerate(trend_metrics, 1):
        fig_trend.add_trace(go.Scatter(
            x=all_days, y=vals, name=label,
            line=dict(color=color, width=2),
            hovertemplate="%{x}<br>" + hover + "<extra></extra>",
        ), row=i, col=1)
        yr = tight_range(vals, target=target)
        fig_trend.update_yaxes(
            range=yr, row=i, col=1,
            title=dict(text=label, font=dict(size=10, color=color)),
            gridcolor="#334155", tickfont=dict(size=9),
        )
        if target is not None:
            fig_trend.add_hline(
                y=target, row=i, col=1,
                line=dict(color=color, dash="dot", width=1),
            )

    fig_trend.update_xaxes(gridcolor="#334155")
    fig_trend.update_layout(
        template="plotly_dark", paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        title=dict(text="90-Day Trends (7-day rolling avg)", font=dict(size=16, color=TEXT)),
        showlegend=False,
        margin=dict(l=60, r=20, t=40, b=30), height=550,
    )

    # --- Row 3 Right: Weight Chart ---
    fig_weight = go.Figure()
    fig_weight.add_trace(go.Scatter(
        x=wt_days, y=wt_vals, name="Daily",
        mode="markers", marker=dict(color=PURPLE, size=6, opacity=0.6),
        hovertemplate="%{x}<br>%{y:.1f} kg<extra></extra>"
    ))
    fig_weight.add_trace(go.Scatter(
        x=wt_days, y=wt_roll, name="14-day avg",
        line=dict(color=PURPLE, width=3),
        hovertemplate="%{x}<br>Avg: %{y:.1f} kg<extra></extra>"
    ))
    if any(f is not None for f in fat_vals):
        fig_weight.add_trace(go.Scatter(
            x=wt_days, y=fat_vals, name="Fat %", yaxis="y2",
            line=dict(color=ORANGE, width=2, dash="dash"),
            hovertemplate="%{x}<br>Fat: %{y:.1f}%<extra></extra>"
        ))
    fig_weight.add_hline(y=TARGET_WEIGHT, line=dict(color=PURPLE, dash="dot", width=1), annotation_text="Target 80 kg", annotation_font_color=PURPLE)

    # Diet phase annotations on weight chart (only show phases in 90-day window)
    weight_phases = [
        ("2021-10-01", "2023-02-28", "Strict Keto"),
        ("2023-03-01", "2024-02-28", "Low Carb"),
        ("2024-03-01", "2024-12-31", "Low Carb (post surgery)"),
        ("2025-01-01", "2025-11-30", "Low Carb"),
        ("2025-12-01", "2026-12-31", "Strict Keto"),
    ]
    for ps, pe, pl in weight_phases:
        if pe >= str(start_date) and ps <= str(end_date):
            fig_weight.add_vrect(
                x0=max(ps, str(start_date)), x1=min(pe, str(end_date)),
                fillcolor="rgba(255,255,255,0.03)", line_width=0,
                annotation_text=pl, annotation_position="top left",
                annotation_font=dict(size=9, color=SUBTEXT),
            )

    fig_weight.update_layout(
        template="plotly_dark", paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        title=dict(text="Weight + Body Composition", font=dict(size=16, color=TEXT)),
        legend=dict(orientation="h", y=-0.15, font=dict(size=11)),
        margin=dict(l=50, r=50, t=40, b=50), height=350,
        yaxis=dict(title="kg", gridcolor="#334155"),
        yaxis2=dict(title="Fat %", overlaying="y", side="right", showgrid=False),
        xaxis=dict(gridcolor="#334155"),
    )

    # --- Row 2 Left: Sleep Consistency (last 14 days) ---
    last_14 = all_days[-14:]
    sleep_durations = [sleep_by_day.get(d, {}).get("sleep_hrs") for d in last_14]
    sleep_colors = [GREEN if s and s >= SLEEP_FLOOR else (RED if s and s < SLEEP_FLOOR else LIGHT_GRAY) for s in sleep_durations]
    short_labels = [d[5:] for d in last_14]

    fig_sleep = go.Figure()
    fig_sleep.add_trace(go.Bar(
        x=short_labels, y=sleep_durations, marker_color=sleep_colors,
        hovertemplate="%{x}<br>%{y:.1f} hrs<extra></extra>"
    ))
    fig_sleep.add_hline(y=SLEEP_FLOOR, line=dict(color=YELLOW, dash="dash", width=2), annotation_text="6hr floor")
    fig_sleep.update_layout(
        template="plotly_dark", paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        title=dict(text="Sleep Duration (14 days)", font=dict(size=14, color=TEXT)),
        margin=dict(l=40, r=20, t=35, b=30), height=250,
        yaxis=dict(range=[4, 9], gridcolor="#334155", title="hours"),
        xaxis=dict(gridcolor="#334155", tickfont=dict(size=9), type="category"),
        showlegend=False,
    )

    # --- Row 2 Right: Weekly Activity Load ---
    # Show last 12 weeks
    weekly_data = []
    for w in range(12):
        week_end = end_date - timedelta(days=w * 7)
        week_start = week_end - timedelta(days=6)
        week_days = [str(week_start + timedelta(days=i)) for i in range(7)]
        cals = [act_by_day[d]["cal"] for d in week_days if d in act_by_day and act_by_day[d]["cal"]]
        weekly_data.append((str(week_start)[5:], sum(cals) if cals else 0))
    weekly_data.reverse()

    fig_weekly = go.Figure()
    wk_labels = [w[0] for w in weekly_data]
    wk_vals = [w[1] for w in weekly_data]
    wk_colors = [GREEN if v >= 3300 else (YELLOW if v >= 2800 else RED) for v in wk_vals]
    fig_weekly.add_trace(go.Bar(
        x=wk_labels, y=wk_vals, marker_color=wk_colors,
        hovertemplate="Week of %{x}<br>%{y:,.0f} cal<extra></extra>"
    ))
    fig_weekly.add_hline(y=3300, line=dict(color=GREEN, dash="dot", width=1), annotation_text="Weight loss zone")
    fig_weekly.update_layout(
        template="plotly_dark", paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        title=dict(text="Weekly Activity Load (active cal)", font=dict(size=14, color=TEXT)),
        margin=dict(l=50, r=20, t=35, b=30), height=250,
        yaxis=dict(gridcolor="#334155"),
        xaxis=dict(gridcolor="#334155", tickfont=dict(size=9), type="category"),
        showlegend=False,
    )

    # --- Row 4 Left: Sleep Quality Heatmap ---
    # Calendar heatmap: composite score per day
    import math
    heatmap_scores = []
    heatmap_days = all_days[-84:]  # 12 weeks
    for d in heatmap_days:
        s = sleep_by_day.get(d, {})
        hr_val = s.get("hr")
        hrv_val = s.get("hrv")
        deep_val = s.get("deep_hrs")
        if hr_val and hrv_val:
            # Score: lower HR better, higher HRV better, more deep better
            hr_score = max(0, min(100, (70 - hr_val) / (70 - 55) * 100))
            hrv_score = max(0, min(100, (hrv_val - 20) / (50 - 20) * 100))
            deep_score = max(0, min(100, (deep_val - 0.5) / (2.0 - 0.5) * 100)) if deep_val else 50
            heatmap_scores.append(hr_score * 0.4 + hrv_score * 0.4 + deep_score * 0.2)
        else:
            heatmap_scores.append(None)

    # Arrange into weeks (rows) x days of week (cols)
    from datetime import datetime
    weeks = []
    week_labels = []
    current_week = []
    current_label = None
    for i, d in enumerate(heatmap_days):
        dt = datetime.strptime(d, "%Y-%m-%d")
        dow = dt.weekday()  # 0=Mon
        if dow == 0 and current_week:
            weeks.append(current_week)
            week_labels.append(current_label)
            current_week = []
        if not current_week:
            current_label = d[5:]
        current_week.append(heatmap_scores[i])
    if current_week:
        # Pad to 7
        while len(current_week) < 7:
            current_week.append(None)
        weeks.append(current_week)
        week_labels.append(current_label)

    # Pad first week
    if weeks:
        dt0 = datetime.strptime(heatmap_days[0], "%Y-%m-%d")
        pad = dt0.weekday()
        if pad > 0:
            weeks[0] = [None] * pad + weeks[0][:7-pad]

    z_data = list(reversed(weeks)) if weeks else [[]]
    y_labels = list(reversed(week_labels)) if week_labels else [""]

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=z_data,
        x=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        y=y_labels,
        colorscale=[[0, RED], [0.4, YELLOW], [0.7, "#86efac"], [1.0, GREEN]],
        zmin=0, zmax=100,
        hoverongaps=False,
        hovertemplate="Week %{y} %{x}<br>Score: %{z:.0f}<extra></extra>",
        showscale=False,
    ))
    fig_heatmap.update_layout(
        template="plotly_dark", paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        title=dict(text="Sleep Quality Heatmap (12 weeks)", font=dict(size=14, color=TEXT)),
        margin=dict(l=60, r=20, t=35, b=30), height=300,
        yaxis=dict(tickfont=dict(size=9)),
        xaxis=dict(side="top"),
    )

    # --- Row 4 Right: BDI + SpO2 (stacked) ---
    bdi_days_plot = [d for d in all_days if spo2_by_day.get(d, {}).get("bdi") is not None]
    bdi_vals_plot = [spo2_by_day[d]["bdi"] for d in bdi_days_plot]
    spo2_vals_plot = [spo2_by_day[d].get("spo2") for d in bdi_days_plot]
    bdi_roll_plot = rolling_avg(bdi_vals_plot, window=7)
    spo2_roll_plot = rolling_avg(spo2_vals_plot, window=7)

    # Mouth tape days
    tape_days = [d for d in bdi_days_plot if tags_by_day.get(d, {}).get("mouth_tape")]
    tape_bdi = [spo2_by_day[d]["bdi"] for d in tape_days]
    tape_spo2 = [spo2_by_day[d].get("spo2") for d in tape_days]

    fig_bdi = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        row_heights=[1, 1],
    )

    # BDI panel - dots colored by severity + rolling avg line
    fig_bdi.add_trace(go.Scatter(
        x=bdi_days_plot, y=bdi_vals_plot, name="BDI",
        mode="markers",
        marker=dict(
            size=7, opacity=0.5,
            color=[RED if b >= 10 else (YELLOW if b >= 6 else BLUE) for b in bdi_vals_plot],
        ),
        hovertemplate="%{x}<br>BDI: %{y:.1f}<extra></extra>"
    ), row=1, col=1)
    fig_bdi.add_trace(go.Scatter(
        x=bdi_days_plot, y=bdi_roll_plot, name="BDI (7-day avg)",
        line=dict(color=ORANGE, width=3),
        hovertemplate="%{x}<br>BDI avg: %{y:.1f}<extra></extra>"
    ), row=1, col=1)
    if tape_days:
        fig_bdi.add_trace(go.Scatter(
            x=tape_days, y=tape_bdi, name="Mouth tape night",
            mode="markers", marker=dict(color=GREEN, size=12, symbol="diamond", line=dict(width=2, color="white")),
            hovertemplate="%{x}<br>BDI: %{y:.1f} (tape)<extra></extra>"
        ), row=1, col=1)
    fig_bdi.add_hline(y=TARGET_BDI, row=1, col=1, line=dict(color=ORANGE, dash="dot", width=1), annotation_text="target")
    # Color zones
    bdi_range = tight_range(bdi_vals_plot, pad_pct=0.1, target=TARGET_BDI)
    fig_bdi.add_hrect(y0=0, y1=4, row=1, col=1, fillcolor=GREEN, opacity=0.07, line_width=0)
    fig_bdi.add_hrect(y0=6, y1=10, row=1, col=1, fillcolor=YELLOW, opacity=0.05, line_width=0)
    fig_bdi.add_hrect(y0=10, y1=max(bdi_range[1], 15), row=1, col=1, fillcolor=RED, opacity=0.05, line_width=0)

    # SpO2 panel - dots + rolling avg
    fig_bdi.add_trace(go.Scatter(
        x=bdi_days_plot, y=spo2_vals_plot, name="SpO2",
        mode="markers",
        marker=dict(size=6, opacity=0.4, color=PURPLE),
        hovertemplate="%{x}<br>SpO2: %{y:.1f}%<extra></extra>"
    ), row=2, col=1)
    fig_bdi.add_trace(go.Scatter(
        x=bdi_days_plot, y=spo2_roll_plot, name="SpO2 (7-day avg)",
        line=dict(color=PURPLE, width=3),
        hovertemplate="%{x}<br>SpO2 avg: %{y:.1f}%<extra></extra>"
    ), row=2, col=1)
    if tape_days:
        fig_bdi.add_trace(go.Scatter(
            x=tape_days, y=tape_spo2, name="Mouth tape night ",
            mode="markers", marker=dict(color=GREEN, size=12, symbol="diamond", line=dict(width=2, color="white")),
            hovertemplate="%{x}<br>SpO2: %{y:.1f}% (tape)<extra></extra>",
            showlegend=False,
        ), row=2, col=1)

    spo2_range = tight_range([v for v in spo2_vals_plot if v], pad_pct=0.15)
    fig_bdi.update_yaxes(title=dict(text="BDI", font=dict(size=11, color=ORANGE)), range=bdi_range, gridcolor="#334155", tickfont=dict(size=9), row=1, col=1)
    fig_bdi.update_yaxes(title=dict(text="SpO2 %", font=dict(size=11, color=PURPLE)), range=spo2_range, gridcolor="#334155", tickfont=dict(size=9), row=2, col=1)
    fig_bdi.update_xaxes(gridcolor="#334155")

    fig_bdi.update_layout(
        template="plotly_dark", paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        title=dict(text="Breathing: BDI + SpO2", font=dict(size=14, color=TEXT)),
        legend=dict(orientation="h", y=-0.12, font=dict(size=10)),
        margin=dict(l=55, r=20, t=35, b=50), height=400,
    )

    # --- Labs Timeline ---
    # Diet phases for annotation
    diet_phases = [
        ("2021-10-01", "2023-02-28", "Strict Keto", "rgba(220,38,38,0.12)"),
        ("2023-03-01", "2024-02-28", "Low Carb", "rgba(59,130,246,0.12)"),
        ("2024-03-01", "2024-12-31", "Low Carb (post surgery)", "rgba(234,179,8,0.12)"),
        ("2025-01-01", "2025-11-30", "Low Carb", "rgba(59,130,246,0.12)"),
        ("2025-12-01", "2026-12-31", "Strict Keto", "rgba(220,38,38,0.12)"),
    ]

    # Pivot labs into series by test
    lab_series = {}
    for row in labs:
        test = row["test"]
        if test not in lab_series:
            lab_series[test] = {"dates": [], "values": []}
        lab_series[test]["dates"].append(row["date"])
        lab_series[test]["values"].append(row["value"])

    fig_labs = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        row_heights=[2, 1],
        subplot_titles=("Lipid Panel + ApoB", "Metabolic Markers"),
    )

    # Add diet phase backgrounds to both subplots
    for start, end, label, color in diet_phases:
        for row in [1, 2]:
            fig_labs.add_vrect(
                x0=start, x1=end, row=row, col=1,
                fillcolor=color, line_width=0,
                annotation_text=label if row == 1 else None,
                annotation_position="top left" if row == 1 else None,
                annotation_font=dict(size=9, color=SUBTEXT) if row == 1 else None,
            )

    # Lipid lines (top subplot)
    lipid_config = [
        ("total_cholesterol", "TC", "#f59e0b", "dash"),
        ("ldl", "LDL", RED, "solid"),
        ("hdl", "HDL", GREEN, "solid"),
        ("triglycerides", "TG", BLUE, "dot"),
        ("apob", "ApoB", PURPLE, "solid"),
    ]
    for test, label, color, dash in lipid_config:
        if test in lab_series:
            fig_labs.add_trace(go.Scatter(
                x=lab_series[test]["dates"], y=lab_series[test]["values"],
                name=label, mode="lines+markers",
                line=dict(color=color, width=2, dash=dash),
                marker=dict(size=8),
                hovertemplate=f"%{{x}}<br>{label}: %{{y:.0f}}<extra></extra>",
            ), row=1, col=1)

    # Reference lines
    fig_labs.add_hline(y=100, row=1, col=1, line=dict(color=RED, dash="dot", width=1),
                       annotation_text="LDL optimal <100", annotation_font_color=SUBTEXT, annotation_font_size=9)
    fig_labs.add_hline(y=90, row=1, col=1, line=dict(color=PURPLE, dash="dot", width=1),
                       annotation_text="ApoB <90", annotation_font_color=SUBTEXT, annotation_font_size=9,
                       annotation_position="bottom right")

    # Metabolic markers (bottom subplot)
    metabolic_config = [
        ("hba1c", "HbA1c %", ORANGE, "solid"),
        ("glucose", "Glucose", BLUE, "solid"),
        ("crp", "CRP", RED, "dash"),
    ]
    for test, label, color, dash in metabolic_config:
        if test in lab_series:
            fig_labs.add_trace(go.Scatter(
                x=lab_series[test]["dates"], y=lab_series[test]["values"],
                name=label, mode="lines+markers",
                line=dict(color=color, width=2, dash=dash),
                marker=dict(size=8),
                hovertemplate=f"%{{x}}<br>{label}: %{{y:.1f}}<extra></extra>",
            ), row=2, col=1)

    fig_labs.update_yaxes(title="mg/dL", gridcolor="#334155", row=1, col=1)
    fig_labs.update_yaxes(title="value", gridcolor="#334155", row=2, col=1)
    fig_labs.update_xaxes(gridcolor="#334155")
    fig_labs.update_layout(
        template="plotly_dark", paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        title=dict(text="Lab Results Timeline + Diet Phases", font=dict(size=16, color=TEXT)),
        legend=dict(orientation="h", y=-0.12, font=dict(size=10)),
        margin=dict(l=55, r=20, t=60, b=50), height=500,
    )

    labs_html = fig_labs.to_html(full_html=False, include_plotlyjs=False, div_id="labs")

    # --- Running Volume Chart (long-term) ---
    # Aggregate runs by month
    from collections import defaultdict
    monthly_runs = defaultdict(lambda: {"count": 0, "km": 0, "cal": 0})
    for r in runs:
        if r["date"]:
            month = r["date"][:7]
            monthly_runs[month]["count"] += 1
            monthly_runs[month]["km"] += r["distance_km"] or 0
            monthly_runs[month]["cal"] += r["calories"] or 0

    # Generate all months from first run to now
    if runs:
        from datetime import datetime
        first_month = min(r["date"][:7] for r in runs if r["date"])
        last_month = date.today().strftime("%Y-%m")
        run_months = []
        ym = first_month
        while ym <= last_month:
            run_months.append(ym)
            y, m = int(ym[:4]), int(ym[5:7])
            m += 1
            if m > 12:
                m = 1
                y += 1
            ym = f"{y}-{m:02d}"

        run_km = [monthly_runs[m]["km"] for m in run_months]
        run_counts = [monthly_runs[m]["count"] for m in run_months]

        fig_runs = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                                 row_heights=[2, 1])

        # Monthly km bar chart
        fig_runs.add_trace(go.Bar(
            x=run_months, y=run_km, name="Monthly km",
            marker_color=[GREEN if k >= 15 else (YELLOW if k >= 5 else RED) for k in run_km],
            hovertemplate="%{x}<br>%{y:.1f} km<extra></extra>",
        ), row=1, col=1)

        # 6-month rolling average km/week
        rolling_km_wk = []
        for i in range(len(run_months)):
            start_idx = max(0, i - 5)
            chunk_km = sum(run_km[start_idx:i+1])
            chunk_months = i - start_idx + 1
            rolling_km_wk.append(chunk_km / (chunk_months * 4.33))
        fig_runs.add_trace(go.Scatter(
            x=run_months, y=rolling_km_wk, name="6-mo avg km/wk",
            line=dict(color=PURPLE, width=2),
            hovertemplate="%{x}<br>%{y:.1f} km/wk<extra></extra>",
        ), row=1, col=1)

        # Run count per month
        fig_runs.add_trace(go.Bar(
            x=run_months, y=run_counts, name="Runs/month",
            marker_color=BLUE, opacity=0.7,
            hovertemplate="%{x}<br>%{y} runs<extra></extra>",
        ), row=2, col=1)

        # Add diet phase shading
        for ps, pe, pl, color in diet_phases:
            for row in [1, 2]:
                fig_runs.add_vrect(
                    x0=ps[:7], x1=pe[:7], row=row, col=1,
                    fillcolor=color, line_width=0,
                    annotation_text=pl if row == 1 else None,
                    annotation_position="top left" if row == 1 else None,
                    annotation_font=dict(size=9, color=SUBTEXT) if row == 1 else None,
                )

        # Target line
        fig_runs.add_hline(y=40, row=1, col=1, line=dict(color=GREEN, dash="dot", width=1),
                           annotation_text="10 km/wk target", annotation_font_color=SUBTEXT, annotation_font_size=9)

        fig_runs.update_yaxes(title="km", gridcolor="#334155", row=1, col=1)
        fig_runs.update_yaxes(title="runs", gridcolor="#334155", row=2, col=1)
        fig_runs.update_xaxes(gridcolor="#334155")
        fig_runs.update_layout(
            template="plotly_dark", paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            title=dict(text="Running Volume (Nike Run Club)", font=dict(size=16, color=TEXT)),
            legend=dict(orientation="h", y=-0.08, font=dict(size=10)),
            margin=dict(l=55, r=20, t=60, b=50), height=450,
            showlegend=True, barmode="overlay",
        )
        runs_html = fig_runs.to_html(full_html=False, include_plotlyjs=False, div_id="runs_chart")
    else:
        runs_html = "<p style='color:#94a3b8;text-align:center;padding:40px'>No running data available</p>"

    # --- Bottom Table: Last 14 days ---
    table_rows = []
    for d in last_14:
        s = sleep_by_day.get(d, {})
        a = act_by_day.get(d, {})
        sp = spo2_by_day.get(d, {})
        w = weight_by_day.get(d, {})
        t = tags_by_day.get(d, {})

        steps = a.get("steps")
        cal = a.get("cal")
        slp = s.get("sleep_hrs")
        hr = s.get("hr")
        hrv = s.get("hrv")
        bdi = sp.get("bdi")
        wt = w.get("weight_kg")
        tape = "🩹" if t.get("mouth_tape") else ""
        notes = t.get("notes", "") or ""

        def fmt(v, decimals=0):
            if v is None:
                return "-"
            return f"{v:,.{decimals}f}"

        def cell_color(val, target, lower_better=True, threshold=0.1):
            if val is None:
                return SUBTEXT
            if lower_better:
                if val <= target:
                    return GREEN
                elif val <= target * (1 + threshold):
                    return YELLOW
                return RED
            else:
                if val >= target:
                    return GREEN
                elif val >= target * (1 - threshold):
                    return YELLOW
                return RED

        table_rows.append({
            "date": d[5:],
            "steps": fmt(steps),
            "steps_color": cell_color(steps, TARGET_STEPS, lower_better=False, threshold=0.15),
            "cal": fmt(cal),
            "sleep": fmt(slp, 1),
            "sleep_color": cell_color(slp, SLEEP_FLOOR, lower_better=False, threshold=0.1),
            "hr": fmt(hr),
            "hr_color": cell_color(hr, 60, lower_better=True, threshold=0.08),
            "hrv": fmt(hrv),
            "bdi": fmt(bdi, 1),
            "bdi_color": cell_color(bdi, TARGET_BDI + 2, lower_better=True, threshold=0.3),
            "weight": fmt(wt, 1),
            "tape": tape,
            "notes": notes[:30],
        })

    # Convert figures to HTML divs
    trend_html = fig_trend.to_html(full_html=False, include_plotlyjs=False, div_id="trend")
    weight_html = fig_weight.to_html(full_html=False, include_plotlyjs=False, div_id="weight")
    sleep_html = fig_sleep.to_html(full_html=False, include_plotlyjs=False, div_id="sleep_consist")
    weekly_html = fig_weekly.to_html(full_html=False, include_plotlyjs=False, div_id="weekly")
    heatmap_html = fig_heatmap.to_html(full_html=False, include_plotlyjs=False, div_id="heatmap")
    bdi_html = fig_bdi.to_html(full_html=False, include_plotlyjs=False, div_id="bdi")
    # labs_html is generated below after the labs chart section

    # Build table HTML
    table_header = """
    <tr>
        <th>Date</th><th>Steps</th><th>Cal</th><th>Sleep</th>
        <th>HR</th><th>HRV</th><th>BDI</th><th>Weight</th><th></th><th>Notes</th>
    </tr>"""
    table_body = ""
    for r in reversed(table_rows):
        table_body += f"""
    <tr>
        <td>{r['date']}</td>
        <td style="color:{r['steps_color']}">{r['steps']}</td>
        <td>{r['cal']}</td>
        <td style="color:{r['sleep_color']}">{r['sleep']}</td>
        <td style="color:{r['hr_color']}">{r['hr']}</td>
        <td>{r['hrv']}</td>
        <td style="color:{r['bdi_color']}">{r['bdi']}</td>
        <td>{r['weight']}</td>
        <td>{r['tape']}</td>
        <td class="notes">{r['notes']}</td>
    </tr>"""

    # Scorecard values
    hr_color = score_color(avg_hr, TARGET_HR, lower_is_better=True)
    wt_color = score_color(curr_weight, TARGET_WEIGHT, lower_is_better=True)
    bdi_color = score_color(avg_bdi, TARGET_BDI, lower_is_better=True)
    step_color = score_color(avg_steps, TARGET_STEPS, lower_is_better=False)

    hr_display = f"{avg_hr:.1f}" if avg_hr else "-"
    step_display = f"{avg_steps:,.0f}" if avg_steps else "-"
    bdi_display = f"{avg_bdi:.1f}" if avg_bdi else "-"
    wt_display = f"{curr_weight:.1f}" if curr_weight else "-"

    # Streak color
    streak_color = GREEN if streak >= 5 else (YELLOW if streak >= 2 else RED)

    # Weekly cal color
    wcal_color = GREEN if weekly_cal >= 3300 else (YELLOW if weekly_cal >= 2800 else RED)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Health Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        background: {BG};
        color: {TEXT};
        padding: 20px;
        max-width: 1400px;
        margin: 0 auto;
    }}
    h1 {{
        font-size: 22px;
        font-weight: 600;
        margin-bottom: 4px;
    }}
    .subtitle {{
        color: {SUBTEXT};
        font-size: 13px;
        margin-bottom: 20px;
    }}
    .row {{
        display: grid;
        gap: 16px;
        margin-bottom: 16px;
    }}
    .row-4 {{ grid-template-columns: repeat(4, 1fr); }}
    .row-3 {{ grid-template-columns: 1fr 1fr 1fr; }}
    .row-2 {{ grid-template-columns: 1fr 1fr; }}
    .card {{
        background: {CARD_BG};
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #334155;
    }}
    .scorecard {{
        text-align: center;
    }}
    .scorecard .label {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: {SUBTEXT};
        margin-bottom: 4px;
    }}
    .scorecard .value {{
        font-size: 36px;
        font-weight: 700;
        line-height: 1.1;
    }}
    .scorecard .target {{
        font-size: 12px;
        color: {SUBTEXT};
        margin-top: 2px;
    }}
    .leading-card {{
        text-align: center;
    }}
    .leading-card .label {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: {SUBTEXT};
        margin-bottom: 4px;
    }}
    .leading-card .value {{
        font-size: 28px;
        font-weight: 700;
    }}
    .leading-card .detail {{
        font-size: 12px;
        color: {SUBTEXT};
        margin-top: 2px;
    }}
    .chart-card {{
        padding: 8px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    th {{
        text-align: left;
        padding: 8px 10px;
        border-bottom: 2px solid #334155;
        color: {SUBTEXT};
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    td {{
        padding: 6px 10px;
        border-bottom: 1px solid #1e293b;
        font-variant-numeric: tabular-nums;
    }}
    tr:hover td {{
        background: #1e293b;
    }}
    .notes {{
        color: {SUBTEXT};
        font-size: 12px;
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .log-btn {{
        display: inline-block;
        color: white;
        padding: 10px 18px;
        border-radius: 8px;
        border: none;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        font-family: inherit;
    }}
    .log-btn:hover {{ opacity: 0.85; }}
    @media (max-width: 900px) {{
        .row-4 {{ grid-template-columns: repeat(2, 1fr); }}
        .row-3 {{ grid-template-columns: 1fr; }}
        .row-2 {{ grid-template-columns: 1fr; }}
    }}
</style>
</head>
<body>

<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
<div>
<h1>Health Dashboard</h1>
<p class="subtitle">Updated {date.today().strftime('%B %d, %Y')} &nbsp;·&nbsp; 7-day averages vs targets</p>
</div>
<div style="display:flex;gap:10px">
<a href="#" onclick="openLocal('/log/tape?token={log_token}');return false" class="log-btn" style="background:{BLUE}">🩹 Log Mouth Tape</a>
<button onclick="logNote()" class="log-btn" style="background:{PURPLE}">📝 Add Note</button>
<a href="#" onclick="openLocal('/refresh?token={log_token}');return false" class="log-btn" style="background:{GREEN}">🔄 Refresh</a>
<a href="#" onclick="setServerIP();return false" style="color:{SUBTEXT};font-size:18px;padding:10px;text-decoration:none" title="Set server IP">⚙️</a>
</div>
</div>
<script>
var SERVER_PORT = 8097;
var LOG_TOKEN = "{log_token}";
var DEFAULT_IP = "{local_ip}";
function getServerBase() {{
    var ip = localStorage.getItem('hd_server_ip') || DEFAULT_IP;
    return 'http://' + ip + ':' + SERVER_PORT;
}}
function setServerIP() {{
    var current = localStorage.getItem('hd_server_ip') || DEFAULT_IP;
    var ip = prompt("Enter your Mac's local IP (e.g. 192.168.1.100):", current);
    if (ip) {{
        localStorage.setItem('hd_server_ip', ip.trim());
        alert('Server IP saved: ' + ip.trim());
    }}
}}
function openLocal(path) {{
    window.open(getServerBase() + path, '_blank');
}}
function logNote() {{
    var note = prompt("Note for today:");
    if (note) {{
        openLocal('/log/note?token=' + LOG_TOKEN + '&text=' + encodeURIComponent(note));
    }}
}}
</script>

<!-- Scorecard -->
<div class="row row-4">
    <div class="card scorecard">
        <div class="label">Overnight HR</div>
        <div class="value" style="color:{hr_color}">{hr_display}</div>
        <div class="target">target: {TARGET_HR} bpm</div>
    </div>
    <div class="card scorecard">
        <div class="label">Weight</div>
        <div class="value" style="color:{wt_color}">{wt_display}</div>
        <div class="target">target: {TARGET_WEIGHT} kg</div>
    </div>
    <div class="card scorecard">
        <div class="label">BDI</div>
        <div class="value" style="color:{bdi_color}">{bdi_display}</div>
        <div class="target">target: &lt;{TARGET_BDI}</div>
    </div>
    <div class="card scorecard">
        <div class="label">Daily Steps</div>
        <div class="value" style="color:{step_color}">{step_display}</div>
        <div class="target">target: {TARGET_STEPS:,}</div>
    </div>
</div>

<!-- Leading Indicators -->
<div class="row row-3">
    <div class="card leading-card">
        <div class="label">Step Streak ({STEP_STREAK_THRESHOLD//1000}K+)</div>
        <div class="value" style="color:{streak_color}">{streak} days</div>
        <div class="detail">Consecutive days compound recovery</div>
    </div>
    <div class="card leading-card">
        <div class="label">Weekly Calorie Load</div>
        <div class="value" style="color:{wcal_color}">{weekly_cal:,}</div>
        <div class="detail">Weight loss zone: 3,300+</div>
    </div>
    <div class="card leading-card">
        <div class="label">Sleep Consistency</div>
        <div class="value" style="color:{GREEN if sum(1 for s in sleep_durations[-7:] if s and s >= SLEEP_FLOOR) >= 5 else YELLOW}">{sum(1 for s in sleep_durations[-7:] if s and s >= SLEEP_FLOOR)}/7</div>
        <div class="detail">Nights ≥{SLEEP_FLOOR}hrs this week</div>
    </div>
</div>

<!-- Charts Row 1 -->
<div class="row row-2">
    <div class="card chart-card">{sleep_html}</div>
    <div class="card chart-card">{weekly_html}</div>
</div>

<!-- Charts Row 2 -->
<div class="row row-2">
    <div class="card chart-card">{trend_html}</div>
    <div class="card chart-card">{weight_html}</div>
</div>

<!-- Charts Row 3 -->
<div class="row row-2">
    <div class="card chart-card">{heatmap_html}</div>
    <div class="card chart-card">{bdi_html}</div>
</div>

<!-- Running + Labs -->
<div class="row row-2">
    <div class="card chart-card">{runs_html}</div>
    <div class="card chart-card">{labs_html}</div>
</div>

<!-- Daily Log -->
<div class="card" style="margin-top: 16px; overflow-x: auto;">
    <h3 style="font-size: 14px; margin-bottom: 12px; color: {SUBTEXT}; text-transform: uppercase; letter-spacing: 1px;">Daily Log — Last 14 Days</h3>
    <table>
        {table_header}
        {table_body}
    </table>
</div>

</body>
</html>"""

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html)
    print(f"Dashboard written to {OUT_PATH}")
    conn.close()

    # Generate encrypted version for GitHub Pages
    encrypt_dashboard(html)


def encrypt_dashboard(html_content):
    """Encrypt dashboard HTML with AES-GCM for static hosting."""
    if not PASSWORD_FILE.exists():
        import secrets
        pwd = secrets.token_urlsafe(16)
        PASSWORD_FILE.write_text(pwd)
        print(f"Generated dashboard password: {pwd}")
        print(f"Saved to {PASSWORD_FILE}")
    else:
        pwd = PASSWORD_FILE.read_text().strip()

    # Encrypt with AES-256-GCM using Web Crypto compatible format
    salt = os.urandom(16)
    iv = os.urandom(12)

    # Derive key with PBKDF2
    key = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt, 100000)

    # AES-GCM encrypt
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, html_content.encode("utf-8"), None)

    # Encode for embedding
    payload = {
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ct": base64.b64encode(ciphertext).decode(),
    }

    encrypted_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Health Dashboard</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        background: #0f172a; color: #f1f5f9;
        display: flex; align-items: center; justify-content: center;
        min-height: 100vh;
    }}
    .login {{
        text-align: center; padding: 40px;
    }}
    .login h1 {{ font-size: 24px; margin-bottom: 20px; }}
    .login input {{
        padding: 12px 16px; font-size: 16px; border-radius: 8px;
        border: 1px solid #334155; background: #1e293b; color: #f1f5f9;
        width: 260px; text-align: center;
    }}
    .login button {{
        display: block; margin: 16px auto 0; padding: 12px 32px;
        font-size: 16px; border-radius: 8px; border: none;
        background: #3b82f6; color: white; cursor: pointer;
        font-weight: 600;
    }}
    .login button:hover {{ opacity: 0.85; }}
    .error {{ color: #ef4444; margin-top: 12px; font-size: 14px; display: none; }}
</style>
</head>
<body>
<div class="login" id="login">
    <h1>Health Dashboard</h1>
    <p style="color:#94a3b8;font-size:13px;margin-bottom:16px" id="auto-msg"></p>
    <input type="password" id="pwd" placeholder="Password" autofocus
        onkeydown="if(event.key==='Enter')decrypt()">
    <button onclick="decrypt()">Unlock</button>
    <p class="error" id="err">Wrong password</p>
</div>
<script>
const payload = {json.dumps(payload)};

async function tryDecrypt(pwd) {{
    const enc = new TextEncoder();
    const salt = Uint8Array.from(atob(payload.salt), c => c.charCodeAt(0));
    const iv = Uint8Array.from(atob(payload.iv), c => c.charCodeAt(0));
    const ct = Uint8Array.from(atob(payload.ct), c => c.charCodeAt(0));

    const keyMaterial = await crypto.subtle.importKey(
        'raw', enc.encode(pwd), 'PBKDF2', false, ['deriveKey']
    );
    const key = await crypto.subtle.deriveKey(
        {{ name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256' }},
        keyMaterial,
        {{ name: 'AES-GCM', length: 256 }},
        false,
        ['decrypt']
    );
    const decrypted = await crypto.subtle.decrypt(
        {{ name: 'AES-GCM', iv: iv }}, key, ct
    );
    const html = new TextDecoder().decode(decrypted);
    localStorage.setItem('hd_pwd', pwd);
    document.open();
    document.write(html);
    document.close();
}}

async function decrypt() {{
    const pwd = document.getElementById('pwd').value;
    const err = document.getElementById('err');
    err.style.display = 'none';
    try {{
        await tryDecrypt(pwd);
    }} catch(e) {{
        err.style.display = 'block';
        localStorage.removeItem('hd_pwd');
    }}
}}

// Auto-unlock with saved password
(async function() {{
    const saved = localStorage.getItem('hd_pwd');
    if (saved) {{
        document.getElementById('auto-msg').textContent = 'Unlocking...';
        try {{
            await tryDecrypt(saved);
        }} catch(e) {{
            localStorage.removeItem('hd_pwd');
            document.getElementById('auto-msg').textContent = 'Saved password expired. Please re-enter.';
        }}
    }}
}})()
</script>
</body>
</html>"""

    ENCRYPTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENCRYPTED_PATH.write_text(encrypted_html)
    print(f"Encrypted dashboard written to {ENCRYPTED_PATH}")


if __name__ == "__main__":
    build_dashboard()
