"""Tiny local server for logging daily tags and triggering refreshes via browser."""

import http.server
import json
import secrets
import sqlite3
import subprocess
import threading
import urllib.parse
from datetime import date
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "data" / "oura.db"
TOKEN_FILE = PROJECT_DIR / "data" / "log_token.txt"
PYTHON = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
PORT = 8097

# Generate a secret token on first run, reuse thereafter
if TOKEN_FILE.exists():
    SECRET = TOKEN_FILE.read_text().strip()
else:
    SECRET = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(SECRET)
    print(f"Generated log token: {SECRET}")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_tags (
            day TEXT PRIMARY KEY,
            mouth_tape INTEGER DEFAULT 0,
            notes TEXT
        )
    """)
    return conn


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        # Check token
        token = qs.get("token", [None])[0]
        if token != SECRET:
            self.send_response(403)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        if parsed.path == "/log/tape":
            day = qs.get("day", [str(date.today())])[0]
            conn = get_conn()
            conn.execute(
                "INSERT INTO daily_tags (day, mouth_tape) VALUES (?, 1) "
                "ON CONFLICT(day) DO UPDATE SET mouth_tape = 1",
                [day]
            )
            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"""<html><body style="background:#0f172a;color:#f1f5f9;
                font-family:system-ui;display:flex;align-items:center;justify-content:center;
                height:100vh;font-size:24px">
                ✅ Mouth tape logged for {day}
                <script>setTimeout(()=>window.close(), 2000)</script>
                </body></html>""".encode())

        elif parsed.path == "/log/note":
            day = qs.get("day", [str(date.today())])[0]
            note = qs.get("text", [""])[0]
            if note:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO daily_tags (day, notes) VALUES (?, ?) "
                    "ON CONFLICT(day) DO UPDATE SET notes = "
                    "CASE WHEN notes IS NULL THEN ? ELSE notes || '; ' || ? END",
                    [day, note, note, note]
                )
                conn.commit()
                conn.close()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"""<html><body style="background:#0f172a;color:#f1f5f9;
                font-family:system-ui;display:flex;align-items:center;justify-content:center;
                height:100vh;font-size:24px">
                ✅ Note logged for {day}: {note}
                <script>setTimeout(()=>window.close(), 2000)</script>
                </body></html>""".encode())

        elif parsed.path == "/refresh":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"""<html><body style="background:#0f172a;color:#f1f5f9;
                font-family:system-ui;display:flex;align-items:center;justify-content:center;
                height:100vh;font-size:24px">
                Refreshing dashboard... (takes ~15s)
                </body></html>""")

            def run_refresh():
                scripts = PROJECT_DIR / "scripts"
                for script in ["fetch_oura.py", "fetch_withings.py", "dashboard.py"]:
                    subprocess.run([PYTHON, str(scripts / script)], cwd=str(PROJECT_DIR))
                # Push to GitHub Pages
                subprocess.run(["git", "add", "docs/index.html"], cwd=str(PROJECT_DIR))
                subprocess.run(["git", "commit", "-m", f"Update dashboard {date.today()}"],
                               cwd=str(PROJECT_DIR))
                subprocess.run(["git", "push"], cwd=str(PROJECT_DIR))

            threading.Thread(target=run_refresh, daemon=True).start()

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Log server running on http://localhost:{PORT}")
    print(f"  Log tape: http://localhost:{PORT}/log/tape")
    print(f"  Log note: http://localhost:{PORT}/log/note?text=your+note")
    server.serve_forever()
