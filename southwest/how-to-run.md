# Southwest Airlines Award Search — How to Run

## Overview

The Southwest scraper uses a headless Playwright browser to navigate to
Southwest's booking page and **intercepts** the internal JSON shopping API
call (`/api/air-booking/v1/air-booking/page/air/booking/shopping`).

Because Southwest's anti-bot layer (Akamai) generates dynamic request headers
in the browser itself, we let the real browser make the call and simply capture
the response — no manual cookie/token extraction required.

---

## Prerequisites

1. Python 3.11+
2. Install dependencies (from the project root):

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Configuration (`config.py`)

Edit the top of `config.py` to set your search parameters:

```python
ORIGINS      = ["SEA"]          # list of departure airport codes
DESTINATIONS = ["SAN", "LAS"]  # list of arrival airport codes
DATE_RANGE_DAYS = 7             # how many days ahead to search

SOUTHWEST_DB_PATH = "output/southwest_awards.db"

DELAY_MIN = 8    # seconds between searches (be polite)
DELAY_MAX = 15
```

> **Note:** Southwest only operates domestic US routes. It does not serve
> international destinations like NRT or LHR.

---

## Running the search

From the **project root**:

```bash
# Search all origins × destinations × next DATE_RANGE_DAYS dates
python southwest/run_southwest_search.py

# Search a single specific date
python southwest/run_southwest_search.py --date 2026-08-13
```

---

## Output

Results are stored in a SQLite database at the path set by `SOUTHWEST_DB_PATH`
(default: `output/southwest_awards.db`).

Schema — `southwest_awards` table:

| Column          | Type    | Description                                      |
|-----------------|---------|--------------------------------------------------|
| id              | INTEGER | Auto-increment primary key                       |
| searched_at     | TEXT    | UTC timestamp of the search                      |
| origin          | TEXT    | Originating airport code (e.g. SEA)              |
| destination     | TEXT    | Destination airport code (e.g. SAN)              |
| flight_date     | TEXT    | Date of travel (YYYY-MM-DD)                      |
| flight_number   | TEXT    | e.g. "WN 3538"                                   |
| departure_time  | TEXT    | ISO-8601 departure datetime                      |
| arrival_time    | TEXT    | ISO-8601 arrival datetime                        |
| carrier         | TEXT    | Always "WN"                                      |
| fare_type       | TEXT    | wanna_get_away / wanna_get_away_plus / anytime / business_select |
| miles           | INTEGER | Rapid Rewards points cost                        |
| taxes_usd       | REAL    | Cash taxes & fees in USD                         |
| stops           | INTEGER | Number of intermediate stops                     |
| duration_min    | INTEGER | Total itinerary duration in minutes              |

### Quick query examples

```sql
-- Cheapest Wanna Get Away fares
SELECT flight_date, flight_number, miles, taxes_usd, stops
FROM southwest_awards
WHERE fare_type = 'wanna_get_away'
ORDER BY miles ASC
LIMIT 20;

-- All nonstop options
SELECT *
FROM southwest_awards
WHERE stops = 0
ORDER BY flight_date, miles;
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `no API response captured` | Page timed out before the API call fired | Increase `timeout=90_000` in `scraper.py`, or check your network |
| `no availability` | Route/date genuinely has no award space | Try a different date or route |
| Browser crashes / launch error | Playwright chromium not installed | Run `playwright install chromium` |

