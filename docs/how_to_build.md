# How to Build an Award Search Tool for a New Airline

This document is written for an AI agent picking up this codebase to add support for a new airline. Read it fully before writing any code.

---

## Project layout

```
awardsearchtool/
├── alaska/
│   ├── scraper.py      ← Playwright page loader + data extractor
│   └── parser.py       ← flattens airline-specific rows → standard award dicts
├── config.py           ← search matrix (origins, destinations, date range)
├── db.py               ← SQLite schema + insert helpers (shared, do not modify)
├── alaska/run_alaska_search.py ← Alaska orchestrator
├── output/alaska_awards.db    ← results land here
└── docs/
    └── how_to_build.md ← this file
```

`db.py` and the runner scripts are airline-specific. For a new airline, create a new package (e.g. `united/`) with the same two files: `scraper.py` and `parser.py`.

---

## Step 1 — Human reconnaissance (do this before writing any code)

This step cannot be automated. A human must capture what the airline's site actually sends.

1. Open the airline's award search page in Chrome.
2. Open DevTools → **Network** tab → filter by **Fetch/XHR**.
3. Run an award search (select "Use Miles" or equivalent, pick a real route and date).
4. Watch the network requests appear. You are looking for the one that carries flight/fare data.

**Two things to determine:**

### A. What format does the data come in?

| What you see in DevTools | Format |
|--------------------------|--------|
| A request with `Content-Type: application/json` and readable JSON in the Preview tab | **JSON API** |
| No clean API call; data appears to be loaded with the page | **HTML-embedded** |

### B. How is the page structured?

- Does the site use **server-side rendering** (SSR)? The page HTML contains the data in a `<script>` tag. Playwright's `page.evaluate()` can extract it. Alaska Airlines is an example of this (SvelteKit SSR).
- Does the site make a clean **XHR/fetch POST or GET** after page load? Copy that request as cURL. This is the easier path — use `requests` instead of Playwright for the actual data fetch.

Save a real sample of the data:
- For JSON API: copy the response body → `sample_<airline>.json`
- For HTML: copy the full page source → `sample_<airline>.html`

---

## Step 2 — Understand the data structure

Open your sample file and find the flight data. You need to locate five fields per flight option:

| Field | What to look for |
|-------|-----------------|
| Flight number | A carrier code + number, e.g. `"AS"` + `505` |
| Departure time | ISO-8601 datetime string |
| Arrival time | ISO-8601 datetime string |
| Miles cost | An integer, often named `points`, `miles`, `award_miles`, `atmosPoints` |
| Taxes / fees | A float, often `taxes`, `grandTotal`, `totalFees` |
| Seats remaining | An integer, often `seatsRemaining`, `availableSeats` |

Also identify:
- How fare classes / cabin types are structured (separate objects? a key per cabin?)
- Whether one API call returns all cabins or requires separate requests per cabin

---

## Step 3 — Build `<airline>/scraper.py`

Create `<airline>/scraper.py` with a single public function:

```python
def fetch_flight_rows(origin: str, destination: str, date: str) -> list[dict]:
    ...
```

It must return the raw list of flight itinerary objects (airline-specific shape). The parser handles normalization. Choose the implementation pattern based on what you found in Step 1.

---

### Pattern A — HTML-embedded data (SvelteKit / SSR pages)

Use this when the data is baked into the page HTML at load time and no separate XHR carries it.

**How Alaska Airlines works (the reference implementation):**

Alaska uses SvelteKit SSR. The results page embeds flight data as a JS object literal inside a `<script>` tag:

```js
__sveltekit_xyz.resolve(2, () => [{
    departureStation: "SEA",
    rows: [{ segments: [...], solutions: {...} }]
}])
```

`alaska/scraper.py` uses Playwright to:
1. Navigate to the search URL (`wait_until="networkidle"`).
2. Run `page.evaluate()` with an injected JS function that:
   - Finds the `<script>` tag containing both `"departureStation"` and `"atmosPoints"` (unique markers for the data block).
   - Uses a bracket-counting loop to extract the full JS data block (handles nested objects/arrays correctly).
   - Calls `eval()` on the extracted block inside the browser — this is safe and correct because `eval()` handles JS-native types (`void 0`, unquoted keys) that would break `json.loads()`.
   - Returns `data[0].rows`.

**Search URL pattern for Alaska:**
```
https://www.alaskaair.com/search/results
  ?O={origin}&D={destination}&OD={date}&A=1&ShoppingMethod=onlineaward&RT=false&locale=en-us
```

**Key insight:** Alaska also exposes a `/__data.json` endpoint, but it is only requested during SvelteKit *client-side* navigation (clicking links within the site). A direct `page.goto()` always triggers SSR and embeds the data in HTML. Do not try to intercept `__data.json` — it will never fire on a fresh page load.

**Template for a new SSR airline:**

```python
from playwright.sync_api import sync_playwright

_BASE_URL = "https://www.example-airline.com/award-search"

# Adapt these two string markers to whatever unique strings appear
# in the airline's data script block.
_MARKER_1 = "departureStation"   # something that only appears in the data script
_MARKER_2 = "pointsCost"         # a field name unique to fare/award data

_EXTRACT_JS = f"""
() => {{
    function extractBlock(text, start) {{
        let depth = 0, inStr = false, strChar = null;
        for (let i = start; i < text.length; i++) {{
            const c = text[i];
            if (inStr) {{
                if (c === '\\\\') {{ i++; continue; }}
                if (c === strChar) inStr = false;
            }} else {{
                if (c === '"' || c === "'" || c === '`') {{ inStr = true; strChar = c; }}
                else if ('{{[('.includes(c)) depth++;
                else if ('}})'.includes(c) || c === ']') {{
                    if (--depth === 0) return text.slice(start, i + 1);
                }}
            }}
        }}
        return null;
    }}

    for (const s of document.querySelectorAll('script')) {{
        const text = s.textContent;
        if (!text.includes('{_MARKER_1}') || !text.includes('{_MARKER_2}')) continue;
        // Adapt this regex to match the framework's data wrapper call
        const re = /\\.resolve\\((\\d+),\\s*\\(\\)\\s*=>\\s*/g;
        let m;
        while ((m = re.exec(text)) !== null) {{
            const block = extractBlock(text, m.index + m[0].length);
            if (!block) continue;
            try {{
                const data = eval(block);
                // Adapt this check to match the actual data shape
                if (Array.isArray(data) && data[0] && Array.isArray(data[0].rows)) {{
                    return data[0].rows;
                }}
            }} catch(e) {{}}
        }}
    }}
    return [];
}}
"""

def build_search_url(origin, destination, date):
    # Adapt query params to the airline's actual URL structure
    return f"{_BASE_URL}?origin={origin}&dest={destination}&date={date}&award=true"

def fetch_flight_rows(origin, destination, date):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 ...")
        page = context.new_page()
        page.goto(build_search_url(origin, destination, date),
                  wait_until="networkidle", timeout=60_000)
        rows = page.evaluate(_EXTRACT_JS)
        browser.close()
    return rows or []
```

---

### Pattern B — JSON API (XHR/fetch call)

Use this when DevTools shows a clean POST or GET that returns JSON with flight data.

**Steps:**
1. Right-click the request in DevTools → **Copy → Copy as cURL**.
2. Inspect the request: note the URL, method (GET or POST), required headers, and payload shape.
3. Save the response body as `sample_<airline>.json`.

**Implementation:**

```python
import requests
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright

_API_URL = "https://www.example-airline.com/api/award/search"  # from cURL
_ua = UserAgent()

# Headers from cURL — include all that are present
_BASE_HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    # add any x-api-key, authorization, referer, etc. from the cURL
}

def _get_session_cookies() -> dict:
    # Airlines require valid session cookies. Use Playwright to visit the
    # homepage and collect them before making API requests.
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=_ua.random)
        page = context.new_page()
        page.goto("https://www.example-airline.com", wait_until="networkidle")
        page.wait_for_timeout(3000)
        raw = context.cookies()
        browser.close()
    return {c["name"]: c["value"] for c in raw}

def _build_payload(origin, destination, date, cabin):
    # Reconstruct the request payload from the cURL Payload tab.
    return {
        "origin": origin,
        "destination": destination,
        "departDate": date,
        "cabin": cabin,
        "isAward": True,
        "passengers": 1,
    }

_session = requests.Session()
_cookies = None

def fetch_flight_rows(origin, destination, date, cabin="coach"):
    global _cookies
    if _cookies is None:
        _cookies = _get_session_cookies()

    headers = {**_BASE_HEADERS, "user-agent": _ua.random}
    cookie_str = "; ".join(f"{k}={v}" for k, v in _cookies.items())
    headers["cookie"] = cookie_str

    resp = _session.post(_API_URL, json=_build_payload(origin, destination, date, cabin),
                         headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()  # return the raw response_calendar; parser will normalize it
```

**Notes for JSON API pattern:**
- Session cookies expire (typically 15–60 min). Re-fetch them if you get 401/403 responses.
- If the airline uses a short-lived `authorization` token in headers, Playwright may need to navigate through the login/search flow to capture it rather than just the homepage.
- Some airlines (Delta, United) use Akamai or Cloudflare — those require real residential IPs or more sophisticated session handling and are out of scope here.

---

## Step 4 — Build `<airline>/parser.py`

Regardless of which scraper pattern you used, `parser.py` must produce this standard shape:

```python
def parse_award_data(rows: list[dict]) -> list[dict]:
    """
    Input:  raw rows list from fetch_flight_rows()
    Output: list of dicts, one per (flight, cabin) combination

    Required keys in each dict:
        flight_number   str    e.g. "AS 505"
        departure_time  str    ISO-8601
        arrival_time    str    ISO-8601
        carrier         str    e.g. "AS"
        cabin           str    "coach" | "business" | "premium" | "first"
        miles           int    points/miles cost
        taxes_usd       float  cash surcharges in USD
        seats           int    seats remaining at this price
        stops           int    0 = nonstop, 1 = one stop, etc.
    """
```

**Alaska Airlines data shape (for reference):**

```
rows[]
  ├── segments[]
  │     ├── publishingCarrier.carrierCode   → carrier
  │     ├── publishingCarrier.flightNumber  → flight_number
  │     ├── departureTime                   → departure_time (first segment)
  │     └── arrivalTime                     → arrival_time (last segment)
  └── solutions{}
        ├── REFUNDABLE_MAIN          → cabin = "coach"
        ├── REFUNDABLE_BUSINESS      → cabin = "business"
        └── REFUNDABLE_PARTNER_PREMIUM → cabin = "premium"
              ├── atmosPoints        → miles
              ├── grandTotal         → taxes_usd
              └── seatsRemaining     → seats
```

All cabins come back in one request — no need to loop per cabin. Other airlines may require separate requests per cabin or use different solution key names.

---

## Step 5 — Wire into the orchestrator

Edit `alaska/run_alaska_search.py` to import your new module:

```python
# Replace these two lines:
from alaska.parser import parse_award_data
from alaska.scraper import fetch_flight_rows

# With:
from united.parser import parse_award_data
from united.scraper import fetch_flight_rows
```

Everything else (`db.py`, `config.py`, the matrix loop, delays, SQLite insert) is shared and unchanged.

---

## Anti-detection checklist

Apply these regardless of which pattern you use:

- **Random delay** between requests: `time.sleep(random.uniform(8, 15))` — already in `alaska/run_alaska_search.py`.
- **Rotate User-Agent**: use `fake_useragent.UserAgent().random` on every request.
- **Session handshake**: always visit the airline homepage first (Playwright) before hitting any API endpoint — this sets tracking cookies that make the session look legitimate.
- **Do not parallelize**: run searches sequentially. Concurrent requests from one IP flag immediately.
- **Avoid round-number delays**: don't use `sleep(10)` exactly — use `uniform(8, 15)`.

---

## Debugging guide

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `fetch_flight_rows` returns `[]` | Markers in `_EXTRACT_JS` don't match this airline's script | Open DevTools, find the data script, update `_MARKER_1` / `_MARKER_2` |
| `fetch_flight_rows` returns `[]` (JSON path) | `__data.json` not fired (SSR page) | Switch to Pattern A |
| HTTP 403 on API call | Session cookies expired or missing | Re-run `_get_session_cookies()` |
| Parser returns empty list | Field names differ from assumed shape | `print(rows[0])` and remap keys |
| Duplicate rows in DB | Same flight in multiple itinerary rows | Add dedup in parser on `(flight_number, cabin, departure_time)` |
| `eval()` throws in browser | Data block regex matched wrong script | Tighten `_MARKER_1` / `_MARKER_2` to more unique strings |
