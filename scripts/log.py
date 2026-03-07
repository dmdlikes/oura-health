"""Quick logging for daily tags (mouth tape, notes, etc.)

Usage:
  python log.py tape              # Log mouth tape for last night
  python log.py tape 2026-03-05   # Log mouth tape for specific date
  python log.py note "ate late"   # Add a note for last night
  python log.py show              # Show recent tags
"""

import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "oura.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def log_tape(day=None):
    day = day or str(date.today())
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_tags (day, mouth_tape) VALUES (?, 1) "
        "ON CONFLICT(day) DO UPDATE SET mouth_tape = 1",
        [day]
    )
    conn.commit()
    conn.close()
    print(f"Logged mouth tape for {day}")


def log_note(note, day=None):
    day = day or str(date.today())
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_tags (day, notes) VALUES (?, ?) "
        "ON CONFLICT(day) DO UPDATE SET notes = "
        "CASE WHEN notes IS NULL THEN ? ELSE notes || '; ' || ? END",
        [day, note, note, note]
    )
    conn.commit()
    conn.close()
    print(f"Logged note for {day}: {note}")


def show_recent(days=14):
    conn = get_conn()
    rows = conn.execute("""
        SELECT t.day, t.mouth_tape, t.notes,
            sp.breathing_disturbance_index,
            s.lowest_heart_rate, s.average_hrv
        FROM daily_tags t
        LEFT JOIN daily_spo2 sp ON sp.day = t.day
        LEFT JOIN sleep s ON s.day = t.day
        ORDER BY t.day DESC LIMIT ?
    """, [days]).fetchall()
    conn.close()

    if not rows:
        print("No tags logged yet.")
        return

    print(f"{'Date':<12} {'Tape':<6} {'BDI':<5} {'HR':<5} {'HRV':<5} {'Notes'}")
    print("-" * 60)
    for r in rows:
        tape = "yes" if r[1] else ""
        bdi = str(r[3]) if r[3] is not None else "-"
        hr = str(r[4]) if r[4] is not None else "-"
        hrv = str(r[5]) if r[5] is not None else "-"
        notes = r[6] or ""
        print(f"{r[0]:<12} {tape:<6} {bdi:<5} {hr:<5} {hrv:<5} {notes}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "tape":
        day = sys.argv[2] if len(sys.argv) > 2 else None
        log_tape(day)
    elif cmd == "note":
        note = sys.argv[2] if len(sys.argv) > 2 else ""
        day = sys.argv[3] if len(sys.argv) > 3 else None
        log_note(note, day)
    elif cmd == "show":
        show_recent()
    else:
        print(__doc__)
