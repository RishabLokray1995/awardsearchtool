# How to Run — Alaska Airlines Award Search

## Prerequisites

From the project root, install dependencies and Playwright's browser binaries (one-time setup):

```bash
cd awardsearchtool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

---

## Running the search

Always run from the **project root** so relative paths (e.g. `output/alaska_awards.db`) resolve correctly.

### Search the next N days (default)

Uses `ORIGINS`, `DESTINATIONS`, and `DATE_RANGE_DAYS` from `config.py`:

```bash
source .venv/bin/activate
python alaska/run_alaska_search.py
```

### Search a specific date

```bash
python alaska/run_alaska_search.py --date 2026-06-19
```

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `ORIGINS` | `["SEA"]` | List of departure airport codes |
| `DESTINATIONS` | `["NRT"]` | List of arrival airport codes |
| `DATE_RANGE_DAYS` | `3` | How many days from today to search |
| `ALASKA_DB_PATH` | `output/alaska_awards.db` | SQLite output path |
| `DELAY_MIN` / `DELAY_MAX` | `8` / `15` | Random sleep range (seconds) between searches |

Multiple origins/destinations are supported — the script runs every combination:

```python
ORIGINS = ["SEA", "LAX"]
DESTINATIONS = ["NRT", "HND"]
DATE_RANGE_DAYS = 7
```

---

## How it works

1. **Scraper** (`alaska/scraper.py`) — builds a search URL and navigates to it with headless Chromium. Alaska uses SvelteKit SSR, so flight data is embedded in a `<script>` tag on the page. A JS snippet extracts and `eval()`s the data block directly in the browser.
2. **Parser** (`alaska/parser.py`) — flattens the raw row data into per-cabin award dicts.
3. **DB** (`db.py`) — inserts results into the `alaska_awards` table in `output/alaska_awards.db`.

---

## Viewing results

```bash
# All results
sqlite3 -column -header output/alaska_awards.db "SELECT * FROM alaska_awards;"

# Best award per date
sqlite3 -column -header output/alaska_awards.db \
  "SELECT flight_date, cabin, MIN(miles) as miles, taxes_usd
   FROM alaska_awards GROUP BY flight_date, cabin ORDER BY flight_date;"
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Script returns "no availability" for all dates | The page JS markers may have changed — inspect the live page and update `_EXTRACT_JS` in `alaska/scraper.py` |
| `playwright._impl._errors.TimeoutError` | Increase `timeout=60_000` in `scraper.py` or check your internet connection |
| Duplicate rows in DB | Re-runs append; delete `output/alaska_awards.db` to start fresh |

