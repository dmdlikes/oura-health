#!/bin/bash
# Daily fetch of Oura and Withings data
cd /Users/dmd/Documents/oura-health
PYTHON=/Library/Frameworks/Python.framework/Versions/3.12/bin/python3
LOG=data/fetch.log

echo "$(date): Starting fetch" >> "$LOG"
$PYTHON scripts/fetch_oura.py >> "$LOG" 2>&1
$PYTHON scripts/fetch_withings.py >> "$LOG" 2>&1
$PYTHON scripts/dashboard.py >> "$LOG" 2>&1
# Push encrypted dashboard to GitHub Pages
git add docs/index.html >> "$LOG" 2>&1
git commit -m "Update dashboard $(date +%Y-%m-%d)" >> "$LOG" 2>&1
git push >> "$LOG" 2>&1
echo "$(date): Done" >> "$LOG"
echo "" >> "$LOG"
