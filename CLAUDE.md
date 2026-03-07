# Oura Health Tracking Project

## Purpose
Ongoing health data analysis using Oura Ring API data. This project persists across Claude Code sessions.

## Key Files
- `data/oura.db` — SQLite database with all Oura ring data
- `journal.md` — Running log of analyses, insights, and discussions
- `scripts/fetch_oura.py` — Script to pull data from Oura API
- `scripts/analyze.py` — Reusable analysis functions
- `scripts/auth_oura.py` — One-time OAuth2 authorization flow
- `.env` — OAuth client ID and secret (DO NOT commit)
- `data/tokens.json` — OAuth access/refresh tokens (DO NOT commit)

## Setup (one-time)
1. Register OAuth app at cloud.ouraring.com → API Applications
2. Set redirect URI to `http://localhost:8099/callback`
3. Add Client ID and Secret to `.env` (see `.env.example`)
4. Run `python scripts/auth_oura.py` → opens browser → approve → tokens saved

## Workflow
1. Run `python scripts/fetch_oura.py` to pull latest data into SQLite (auto-refreshes tokens)
2. Query the database for analysis
3. Append findings to journal.md

## Database Schema
See `scripts/fetch_oura.py` for table definitions. Main tables:
- `sleep` — Sleep sessions with scores, stages, timing
- `daily_readiness` — Readiness scores and contributors
- `daily_activity` — Activity scores, steps, calories
- `heart_rate` — Heart rate samples (5-min intervals)
- `daily_spo2` — Blood oxygen readings

## Withings Scale Integration
- `scripts/auth_withings.py` — One-time OAuth2 authorization for Withings
- `scripts/fetch_withings.py` — Fetches weight/body composition into `weight` table
- `data/withings_tokens.json` — Withings OAuth tokens (DO NOT commit)
- Redirect URI: `http://localhost:8098/callback`
- Weight table: date, weight_kg, fat_ratio_pct, fat_mass_kg, fat_free_mass_kg, muscle_mass_kg, bone_mass_kg, hydration_kg

## Daily Logging
- `scripts/log.py` — CLI for logging mouth tape usage, notes, etc.
- Usage: `python3 log.py tape`, `python3 log.py note "ate late"`, `python3 log.py show`
- Data stored in `daily_tags` table

## Visualization
Data is in SQLite, ready for matplotlib/plotly. Use `scripts/analyze.py` for common queries.
- `scripts/plot_trends.py` — 4 normalized metrics over time
- `scripts/plot_correlations.py` — Paired correlation quadrants
