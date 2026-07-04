# Oura Health — Setup & Architecture

This is the durable "how the whole thing works" doc. If something breaks (especially
after a **machine migration**), start with the [Troubleshooting](#troubleshooting) and
[New-Machine Checklist](#new-machine-migration-checklist) sections — they cover every
failure we've actually hit.

> TL;DR of the architecture: there are **two independent pipelines**. The **GitHub
> Action** is the always-on backbone (fetches data, publishes the encrypted dashboard,
> rotates its own tokens) and is machine-independent. The **local LaunchAgent** is a
> convenience that only keeps the *local* `data/oura.db` fresh. Either can run without
> the other.

---

## 1. What this project does

Pulls personal health data from the **Oura Ring API** (sleep, readiness, activity,
heart rate, SpO2, daytime stress, resilience) and the **Withings API** (weight / body
composition) into a local SQLite DB (`data/oura.db`), and publishes a password-encrypted
dashboard to GitHub Pages.

---

## 2. Architecture (two independent pipelines)

```
                          ┌─────────────────────────────────────────────┐
   OURA API  ─┐           │  CLOUD: GitHub Action (daily-refresh.yml)     │
   WITHINGS ──┼──────────▶│  cron 13:00 UTC (08:00 ET)                    │
              │           │   • downloads oura.db artifact                 │
              │           │   • fetch_oura.py + fetch_withings.py          │
              │           │   • dashboard.py -> docs/index.html (encrypted)│
              │           │   • re-uploads oura.db artifact (90-day)       │
              │           │   • gh secret set OURA_TOKENS/WITHINGS_TOKENS  │
              │           │   • commits & pushes docs/index.html           │
              │           └─────────────────────────────────────────────┘
              │                              │ publishes
              │                              ▼
              │                    GitHub Pages dashboard (AES-encrypted)
              │
              │           ┌─────────────────────────────────────────────┐
              └──────────▶│  LOCAL: LaunchAgent com.dmd.oura-fetch        │
                          │  cron 08:00 local, runs scripts/fetch_all.sh  │
                          │   • fetch_oura.py + fetch_withings.py          │
                          │   • writes local data/oura.db ONLY            │
                          │   • does NOT build/push the dashboard          │
                          └─────────────────────────────────────────────┘
```

**Why two?** The Action is reliable and survives machine changes; it owns the public
dashboard and token rotation. The local job exists so `data/oura.db` on this Mac stays
current for ad-hoc analysis, and so intraday heart-rate accumulates locally (the Oura
`heartrate` endpoint only returns ~the last 2 days per call, so history is built up over
time by fetching daily).

**They use independent Oura token grants** (the cloud token lives in a GitHub secret; the
local token in `data/tokens.json`). Oura allows multiple concurrent authorizations, so
they do **not** fight over the single-use refresh token. A stale local token simply 401s
until re-auth; it does not affect the cloud.

---

## 3. Repository layout

| Path | Purpose |
|---|---|
| `scripts/fetch_oura.py` | Pull Oura data into SQLite (auto-refreshes token) |
| `scripts/fetch_withings.py` | Pull Withings weight/body-comp |
| `scripts/auth_oura.py` | One-time Oura OAuth (browser). Port **8099** |
| `scripts/auth_withings.py` | One-time Withings OAuth (browser). Port **8098** |
| `scripts/dashboard.py` | Build the encrypted `docs/index.html` (needs `plotly`) |
| `scripts/fetch_all.sh` | Local daily driver (fetch only — no dashboard/push) |
| `scripts/log_server.py` | Tiny local server (port **8097**) for browser tag-logging + refresh trigger |
| `scripts/log.py` | CLI to log daily tags (`tape`, `note`, `show`) |
| `data/oura.db` | SQLite DB (**gitignored**) |
| `docs/index.html` | Encrypted dashboard (committed; GitHub Pages) |
| `.github/workflows/daily-refresh.yml` | The cloud pipeline |
| `CLAUDE.md` | Higher-level project notes / schema summary |
| `journal.md` | Running analysis log |

### DB tables
`sleep`, `daily_readiness`, `daily_activity`, `heart_rate`, `daily_spo2`,
`daily_stress`, `daily_resilience`, `weight`, `daily_tags`, `runs`, `labs`.

---

## 4. Credentials & secrets

**Local files (all gitignored — see `.gitignore` `data/` + `.env`):**

| File | Contains |
|---|---|
| `.env` | `OURA_CLIENT_ID/SECRET`, `WITHINGS_CLIENT_ID/SECRET` |
| `data/tokens.json` | Oura OAuth access+refresh tokens |
| `data/withings_tokens.json` | Withings OAuth tokens |
| `data/dashboard_password.txt` | Password that encrypts the dashboard |
| `data/log_token.txt` | Secret for the local log server |

**GitHub Action secrets** (Settings → Secrets → Actions): `OURA_CLIENT_ID`,
`OURA_CLIENT_SECRET`, `WITHINGS_CLIENT_ID`, `WITHINGS_CLIENT_SECRET`, `OURA_TOKENS`,
`WITHINGS_TOKENS`, `DASHBOARD_PASSWORD`, `LOG_TOKEN`, `TOKEN_UPDATER_PAT` (a PAT the
Action uses to write the refreshed tokens back into the secrets).

**Dashboard encryption:** PBKDF2-HMAC-SHA256, 100k iterations → AES-GCM-256. To read the
dashboard data programmatically, decrypt `const payload = {salt, iv, ct}` (base64) in
`docs/index.html` with the password in `data/dashboard_password.txt`.

---

## 5. OAuth / re-authorization

Refresh tokens are **single-use** (they rotate on every refresh). If a token chain is
interrupted (e.g. a stale copy), you get `400`/`invalid refresh_token` and must re-auth.

### Oura
```bash
cd ~/Documents/oura-health && python3 scripts/auth_oura.py
```
Opens the browser → log in → **Allow**. Scopes requested:
`daily heartrate workout tag session spo2 personal email stress`.
- On the consent screen the **"sleep"** toggle == the `daily` scope (carries sleep,
  readiness, activity, **daily_stress**).
- **`daily_resilience` requires the separate `stress` toggle** — if it's unchecked you
  get `401 Token is not authorized access stress scope`.
- Redirect URI registered at cloud.ouraring.com must be `http://localhost:8099/callback`.

### Withings
```bash
cd ~/Documents/oura-health && python3 scripts/auth_withings.py
```
Scope `user.metrics`; redirect URI `http://localhost:8098/callback`.

### After re-auth, sync the cloud too (optional)
The Action keeps its own token in the `OURA_TOKENS` secret and rotates it automatically,
so it usually needs no attention. Only if the cloud token dies, update the secret with a
fresh `data/tokens.json` (via the GitHub UI or `gh secret set OURA_TOKENS < data/tokens.json`).

---

## 6. Local automation (LaunchAgents)

Two agents live in `~/Library/LaunchAgents/`:

1. **`com.dmd.oura-fetch.plist`** — daily 08:00 fetch. Runs
   `/bin/bash scripts/fetch_all.sh`; logs to `~/Library/Logs/oura-fetch.log`.
2. **`com.dmd.oura-log-server.plist`** — keeps `log_server.py` running (port 8097).

Manage:
```bash
launchctl load   ~/Library/LaunchAgents/com.dmd.oura-fetch.plist
launchctl unload ~/Library/LaunchAgents/com.dmd.oura-fetch.plist
launchctl kickstart -k gui/$(id -u)/com.dmd.oura-fetch      # run now
launchctl print     gui/$(id -u)/com.dmd.oura-fetch | grep 'last exit code'
```

**Key design choices (learned the hard way):**
- The plist invokes **`/bin/bash <script>`** (not the script directly) and logs
  **outside `~/Documents`** (`~/Library/Logs/`), because launchd + TCC can't write logs
  into the protected Documents folder (that caused `EX_CONFIG`).
- Use **`/usr/bin/python3`** (system Python has `requests` + `cryptography` in the user
  site). Do **not** hardcode a `/Library/Frameworks/Python.framework/.../3.12` path —
  that gets removed on OS upgrades / migrations.
- The local job is **fetch-only**. The dashboard build + `git push` were removed from it
  because the GitHub Action already owns publishing — running both caused push races.

---

## 7. ⚠️ Critical gotchas (read this before debugging)

1. **macOS Full Disk Access does NOT migrate between machines.** TCC permission grants
   live in a per-machine database that Migration Assistant does *not* copy. A LaunchAgent
   that touches `~/Documents` will fail with **`Operation not permitted`** on a new Mac
   until you re-grant FDA. **This is the single thing that broke after the last migration.**
   Fix: System Settings → Privacy & Security → **Full Disk Access** → add **`/bin/bash`**.
2. **Framework Python paths vanish.** Always use `/usr/bin/python3` in automation.
3. **Oura refresh tokens are single-use.** A stale `tokens.json` → `400` on refresh →
   re-run `auth_oura.py`. Cloud and local hold independent grants; they don't conflict.
4. **`daily_resilience` needs the `stress` scope** (not just `daily`).
5. **Oura `heartrate` returns only ~2 days of history.** Intraday HR is only complete
   from the point daily fetching starts running — it accumulates, it can't be backfilled.
6. **Never let the local job push the dashboard** — the Action owns `docs/index.html`.
7. **The dashboard is encrypted** — don't expect readable data in `docs/index.html`.

---

## 8. New-machine / migration checklist

Do these in order on a fresh Mac:

1. `git clone` the repo into `~/Documents/oura-health` (or elsewhere — see note below).
2. Restore the gitignored secret files (not in git): `.env`, `data/tokens.json`,
   `data/withings_tokens.json`, `data/dashboard_password.txt`, `data/log_token.txt`.
   (Or seed the DB + tokens from the GitHub Action's `oura-db` artifact / secrets.)
3. Install deps for system Python:
   `python3 -m pip install --user requests cryptography plotly`
4. **Grant Full Disk Access to `/bin/bash`** (System Settings → Privacy & Security →
   Full Disk Access → `+` → ⌘⇧G → `/bin/bash`). ← the step that's easy to forget.
5. Fix any hardcoded interpreter paths to `/usr/bin/python3`
   (`scripts/fetch_all.sh`, `scripts/log_server.py`, the two plists).
6. `launchctl load` both plists; `kickstart` the fetch agent; confirm `last exit code = 0`.
7. Re-auth if tokens are stale: `python3 scripts/auth_oura.py` (+ `auth_withings.py`).

> Note: if you don't want to grant FDA to bash, put the repo **outside** `~/Documents`
> (e.g. `~/oura-health`) — non-protected locations have no TCC restriction — and update
> the paths in the two plists and `fetch_all.sh`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Operation not permitted` in launchd log | No Full Disk Access on new machine (TCC) | Grant FDA to `/bin/bash` (§7.1) |
| `last exit code = 78 (EX_CONFIG)` | launchd can't exec target / write log in `~/Documents` | Log to `~/Library/Logs`; invoke via `/bin/bash`; grant FDA |
| `no such file or directory .../Python.framework/.../3.12` | Framework Python removed | Switch to `/usr/bin/python3` |
| `400` / `invalid refresh_token` | Stale single-use OAuth token | Re-run `auth_oura.py` / `auth_withings.py` |
| `401 ... access stress scope` | Missing `stress` scope | Re-auth Oura, check the **stress** toggle |
| Dashboard not updating | GitHub Action failing | Check Actions tab; usually a dead `OURA_TOKENS` secret |
| Local `oura.db` stale but dashboard fresh | Local job down, Action fine | Fix local job (§6/§7); or pull the `oura-db` artifact |

---

## The dashboard "🔄 Refresh" button (log server)

The dashboard has Refresh / Log-Mouth-Tape / Log-Note buttons that call the **local log
server** (`log_server.py`, port 8097) via `window.open('http://<host>:8097/...')`.
`/refresh` re-runs fetch + `dashboard.py` + push, republishing the dashboard.

- The host defaults to **`localhost`** (`dashboard.py` sets `local_ip = "localhost"`), so
  it works from a browser **on this Mac** regardless of whether the dashboard was built
  locally or by the cloud Action. `http://localhost` is exempt from https mixed-content
  blocking; a baked-in LAN/runner IP is not (and the Action would bake in an unreachable
  cloud IP).
- To use the buttons from a **phone / another device**, click the dashboard's set-IP
  control and enter the Mac's LAN IP (saved in `localStorage` as `hd_server_ip`).
- The auth token is `data/log_token.txt`, which must equal the `LOG_TOKEN` GitHub secret
  (they currently match). If Refresh returns 403, they've diverged — re-sync the secret.
- Requires the log-server agent running (see §6) and `plotly` installed for the refresh
  rebuild: `python3 -m pip install --user plotly`.

## Known issues (as of 2026-07-04)

- **Local Withings token is dead** (`invalid refresh_token`) — run `auth_withings.py` if
  you want local weight updates; the Action keeps cloud weight fresh regardless.
