"""One-time OAuth 2.0 authorization for Oura API. Run this once to get tokens."""

import http.server
import json
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

ENV_PATH = Path(__file__).parent.parent / ".env"
TOKEN_PATH = Path(__file__).parent.parent / "data" / "tokens.json"
REDIRECT_PORT = 8099
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

AUTHORIZE_URL = "https://cloud.ouraring.com/oauth/authorize"
TOKEN_URL = "https://api.ouraring.com/oauth/token"

SCOPES = "daily heartrate workout tag session spo2 personal email"


def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def save_tokens(tokens):
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(tokens, indent=2))
    print(f"Tokens saved to {TOKEN_PATH}")


def main():
    env = load_env()
    client_id = env.get("OURA_CLIENT_ID")
    client_secret = env.get("OURA_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Missing OURA_CLIENT_ID or OURA_CLIENT_SECRET in .env")
        print("Add them to:", ENV_PATH)
        return

    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "oura_health_auth",
    }
    auth_url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    # Start local server to capture the callback
    auth_code = {}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            qs = urllib.parse.parse_qs(query)

            if "code" in qs:
                auth_code["code"] = qs["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Authorization successful!</h2><p>You can close this tab.</p>")
            else:
                error = qs.get("error", ["unknown"])[0]
                auth_code["error"] = error
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h2>Authorization failed: {error}</h2>".encode())

        def log_message(self, format, *args):
            pass  # Suppress server logs

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)

    print("Opening browser for Oura authorization...")
    print(f"If the browser doesn't open, go to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Handle one request (the callback)
    server.handle_request()
    server.server_close()

    if "error" in auth_code:
        print(f"Authorization failed: {auth_code['error']}")
        return

    if "code" not in auth_code:
        print("No authorization code received.")
        return

    # Exchange code for tokens
    print("Exchanging code for tokens...")
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": auth_code["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    resp.raise_for_status()
    tokens = resp.json()

    save_tokens(tokens)
    print("Authorization complete! You can now run fetch_oura.py")


if __name__ == "__main__":
    main()
