#!/bin/bash
# Daily LOCAL fetch of Oura data into data/oura.db.
# NOTE: dashboard build + git push are intentionally NOT done here — the
# GitHub Action (.github/workflows/daily-refresh.yml) owns publishing the
# dashboard. This job only keeps the local DB fresh (and accumulates the
# intraday heart-rate the API only returns for the last ~2 days).
# NOTE: Withings is intentionally NOT fetched here. Withings refresh tokens are
# single-use, so a local fetch would rotate the token out from under the cloud's
# WITHINGS_TOKENS secret and break the daily dashboard. The CLOUD is the sole
# owner of Withings. (Oura is safe — it issues independent grants per auth.)
cd "$(dirname "$0")/.." || exit 1   # project root, relative to this script (survives moves/spaces)
PYTHON=/usr/bin/python3   # 3.12 framework was removed on machine migration; system python3 has requests+cryptography
LOG=data/fetch.log

echo "$(date): Starting local fetch" >> "$LOG"
$PYTHON scripts/fetch_oura.py >> "$LOG" 2>&1
echo "$(date): Done" >> "$LOG"
echo "" >> "$LOG"
