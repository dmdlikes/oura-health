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
cd "$HOME/Documents/Admin Docs/Claude Project/oura-health" && python3 scripts/auth_oura.py
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
cd "$HOME/Documents/Admin Docs/Claude Project/oura-health" && python3 scripts/auth_withings.py
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

1. `git clone` the repo (current home: `~/Documents/Admin Docs/Claude Project/oura-health`;
   any location works — see the FDA/paths notes below).
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

## The dashboard "🔄 Refresh" / Notes / Mouth-Tape buttons (log server)

These buttons call a server running **on the Mac** (`log_server.py`, port 8097) via
`window.open('http://<host>:8097/...')`. `/refresh` re-runs fetch + `dashboard.py` + push
(republishing the dashboard); `/log/tape` and `/log/note` write to the `daily_tags` table.

**Important reality check (learned 2026-07-04):** the host is `get_local_ip()`, baked at
build time — the Mac's LAN IP when built locally, or the **GitHub runner's IP when the
cloud Action builds it** (which is the normal case). So:
- The buttons only work from a browser **on the same network as the Mac** (with the Mac
  awake, the log-server agent running, and macOS firewall allowing port 8097). From a
  phone on cellular / another network, they **cannot reach the Mac** and the tab hangs.
- A baked-in LAN IP is also **https mixed-content-blocked** in-page; the buttons dodge
  that by using `window.open` (a top-level navigation), but the host still has to be
  reachable.
- There is a set-IP override (`localStorage` key `hd_server_ip`) but no visible button
  wires it, so it's not practically settable on a phone.

**What actually keeps the dashboard current from anywhere is the daily GitHub Action, not
these buttons.** Since 2026-03-10 the Action has rebuilt+republished every morning, so the
data is never more than ~a day stale regardless of the button. The Refresh button was the
pre-Action stopgap and has been largely redundant since.

**If you want true on-demand resync from any device**, the button must trigger the cloud
**Action** (`workflow_dispatch` via the GitHub API), not the Mac. Not currently
implemented — it needs a repo-scoped token embedded in the (encrypted) dashboard.

- Auth token: `data/log_token.txt` must equal the `LOG_TOKEN` GitHub secret (they match).
- Requires the log-server agent running (§6) and `plotly` for the refresh rebuild.

## Withings token ownership — DO NOT re-auth Withings locally

**The CLOUD is the sole owner of the Withings token.** Withings refresh tokens are
single-use (they rotate on every refresh), and unlike Oura, Withings does NOT issue
independent per-authorization grants — so two owners fight and one always ends up dead.

- The local job (`fetch_all.sh`) intentionally **does NOT fetch Withings** — only Oura.
- The cloud Action fetches Withings, rotates the token, and writes it back to the
  `WITHINGS_TOKENS` secret ("Save refreshed tokens" step). Self-sustaining.
- **If you `python3 scripts/auth_withings.py` locally, you WILL break the cloud** — the
  re-auth rotates the token out from under the `WITHINGS_TOKENS` secret. (This is exactly
  what happened 2026-08-21 and blanked the dashboard for 10 days.) To recover: update the
  `WITHINGS_TOKENS` secret (repo → Settings → Secrets and variables → Actions) with the
  contents of `data/withings_tokens.json`, then re-run the workflow.
- Oura is safe to re-auth locally — it issues independent grants, so local and cloud
  coexist.

Also: both fetch steps in `daily-refresh.yml` are `continue-on-error: true`, so a single
dead data-source token can never again blank the whole dashboard — it publishes whatever
succeeded.
