# How to Run — American Airlines Award Search

## Prerequisites

### 1. Install dependencies (one-time)

```bash
cd awardsearchtool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Add your AA session credentials to `config.py` ⚠️

The AA booking API is protected by Akamai and requires real browser session cookies. **You must do this before running the script**, and refresh the values whenever you get HTTP 403 errors (sessions expire after ~15–60 minutes of inactivity).

**Step-by-step:**

1. Open [https://www.aa.com](https://www.aa.com) in Chrome and run any award search (e.g. SEA → NRT, One-way, Use Miles).
2. Open **DevTools** (`⌘ + Option + I`) → **Network** tab → filter by `calendar`.
3. Find the `POST` request to `/booking/api/search/calendar` and click it.
4. **Right-click** the request → **Copy** → **Copy as cURL**.
5. In the cURL output, find:
   - `-b '...'` — the full cookie string → paste into `AA_COOKIE_STRING`
   - `-H 'x-xsrf-token: ...'` — the token value → paste into `AA_XSRF_TOKEN`

```python
# config.py
AA_COOKIE_STRING = "XSRF-TOKEN=abc123; JSESSIONID=xyz; _abck=..."
AA_XSRF_TOKEN    = "a8fad1cf-cd43-4707-9e12-b32aa92050c9"
```

---

## Running the search

Always run from the **project root** so relative paths (e.g. `output/aa_awards.db`) resolve correctly.

### Search the next N days (default)

Uses `ORIGINS`, `DESTINATIONS`, and `DATE_RANGE_DAYS` from `config.py`:

```bash
source .venv/bin/activate
python american/run_aa_search.py
```

### Search a specific date

```bash
python american/run_aa_search.py --date 2026-06-19
```

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `ORIGINS` | `["SEA"]` | List of departure airport codes |
| `DESTINATIONS` | `["NRT"]` | List of arrival airport codes |
| `DATE_RANGE_DAYS` | `3` | How many days from today to search |
| `AA_DB_PATH` | `output/aa_awards.db` | SQLite output path |
| `AA_CABIN` | `"BUSINESS,FIRST"` | Cabin class — see options below |
| `DELAY_MIN` / `DELAY_MAX` | `8` / `15` | Random sleep range (seconds) between searches |

**Valid `AA_CABIN` values:**

| Value | Description |
|---|---|
| `"BUSINESS,FIRST"` | Business + First class awards |
| `"PREMIUM_ECONOMY"` | Premium Economy awards |
| `"COACH"` | Economy awards |

---

## How it works

1. **Scraper** (`american/scraper.py`) — launches headless Chromium and navigates to `aa.com` to establish a valid session (gets XSRF-TOKEN and session cookies). Then fires a `fetch()` call to `POST /booking/api/search/calendar` from within the browser context — same-origin, so all cookies are included automatically.
2. **Parser** (`american/parser.py`) — flattens the calendar response into one award dict per valid day, with miles, taxes, and a `lowest_price` flag.
3. **DB** (`db.py`) — inserts results into the `aa_awards` table in `output/aa_awards.db`.

> **Note:** The AA calendar API returns pricing for the **entire month** in one call. The `departureDate` in the request body is used as the anchor date — AA returns all available days in that calendar month.

---

## Viewing results

```bash
# All results
sqlite3 -column -header output/aa_awards.db "SELECT * FROM aa_awards;"

# Lowest-price days only
sqlite3 -column -header output/aa_awards.db \
  "SELECT flight_date, miles, taxes_usd
   FROM aa_awards WHERE lowest_price = 1
   ORDER BY miles ASC;"

# Best price per route
sqlite3 -column -header output/aa_awards.db \
  "SELECT origin, destination, flight_date, MIN(miles) as miles, taxes_usd
   FROM aa_awards GROUP BY origin, destination, flight_date
   ORDER BY miles ASC;"
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ValueError: AA_COOKIE_STRING and AA_XSRF_TOKEN must be set` | Fill in both fields in `config.py` (see Prerequisites above) |
| `HTTP 403` | Your session has expired — repeat the DevTools steps and update `config.py` |
| `HTTP 401` | Same as 403 — credentials are invalid or missing |
| Returns empty awards list | Calendar API returned `validDay: false` for all days (no availability on that route/date) |
| Duplicate rows in DB | Re-runs append; delete `output/aa_awards.db` to start fresh |

