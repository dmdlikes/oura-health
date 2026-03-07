"""One-time OAuth 2.0 authorization for Withings API."""

import hashlib
import hmac
import http.server
import json
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

ENV_PATH = Path(__file__).parent.parent / ".env"
TOKEN_PATH = Path(__file__).parent.parent / "data" / "withings_tokens.json"
REDIRECT_PORT = 8098
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"
TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
SIGNATURE_URL = "https://wbsapi.withings.net/v2/signature"

SCOPES = "user.metrics"


def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def sign(action, client_id, client_secret, nonce):
    """HMAC SHA-256 signature: action,client_id,nonce signed with client_secret."""
    msg = f"{action},{client_id},{nonce}"
    return hmac.new(client_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


def get_nonce(client_id, client_secret):
    """Fetch a fresh nonce from Withings API."""
    timestamp = str(int(time.time()))
    # Signature for getnonce: getnonce,client_id,timestamp
    msg = f"getnonce,{client_id},{timestamp}"
    signature = hmac.new(client_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

    resp = requests.post(SIGNATURE_URL, data={
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


def save_tokens(tokens):
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(tokens, indent=2))
    print(f"Tokens saved to {TOKEN_PATH}")


def main():
    env = load_env()
    client_id = env.get("WITHINGS_CLIENT_ID")
    client_secret = env.get("WITHINGS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Missing WITHINGS_CLIENT_ID or WITHINGS_CLIENT_SECRET in .env")
        return

    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "withings_health_auth",
    }
    auth_url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    # Start local server to capture callback
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
                self.wfile.write(b"<h2>Withings authorization successful!</h2><p>You can close this tab.</p>")
            else:
                error = qs.get("error", ["unknown"])[0]
                auth_code["error"] = error
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h2>Authorization failed: {error}</h2>".encode())

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)

    print("Opening browser for Withings authorization...")
    print(f"If the browser doesn't open, go to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server.handle_request()
    server.server_close()

    if "error" in auth_code:
        print(f"Authorization failed: {auth_code['error']}")
        return

    if "code" not in auth_code:
        print("No authorization code received.")
        return

    # Exchange code for tokens — must be fast, code expires in 30 seconds
    print("Exchanging code for tokens...")
    nonce = get_nonce(client_id, client_secret)
    action = "requesttoken"
    signature = sign(action, client_id, client_secret, nonce)

    resp = requests.post(TOKEN_URL, data={
        "action": action,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": auth_code["code"],
        "redirect_uri": REDIRECT_URI,
        "nonce": nonce,
        "signature": signature,
    })
    resp.raise_for_status()
    result = resp.json()

    if result.get("status") != 0:
        print(f"Token exchange failed: {result}")
        return

    save_tokens(result.get("body", {}))
    print("Authorization complete!")


if __name__ == "__main__":
    main()
