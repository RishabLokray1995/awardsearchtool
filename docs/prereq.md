# Prerequisites & Setup — Award Search Tool (New Mac)

Follow these steps in order. Each command can be run directly. The tool will not work if any step is skipped.

---

## 1. Verify Python version

```bash
python3 --version
```

Required: **Python 3.10 or higher** (the code uses `str | None` union syntax).

If you have Python 3.9 or older, install a newer version via Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12
```

Then confirm:

```bash
python3.12 --version
```

Use `python3.12` in place of `python3` for all commands below if the system default is too old.

---

## 2. Navigate to the project directory

```bash
cd "/path/to/awardsearchtool"
```

Replace the path with wherever the repo lives on this machine.

---

## 3. Create a virtual environment

```bash
python3 -m venv .venv
```

Confirm it was created:

```bash
ls .venv/bin/python3
```

---

## 4. Install Python dependencies

```bash
.venv/bin/pip install -r requirements.txt
```

Expected: all four packages install without errors (`requests`, `playwright`, `fake-useragent`, `python-dotenv`).

---

## 5. Install the Playwright browser (Chromium)

This downloads the headless browser the scraper controls. It is separate from the Python package.

```bash
.venv/bin/playwright install chromium
```

Expected output ends with something like `Chromium ... downloaded to ...`. If this step is skipped, the scraper will crash immediately with a browser-not-found error.

---

## 6. Create the output directory

`db.py` creates the SQLite file automatically, but the parent directory must exist:

```bash
mkdir -p output
```

---

## 7. Configure the search matrix

Open `config.py` and set the routes and date range you want to search:

```python
ORIGINS = ["SEA"]           # IATA codes for departure airports
DESTINATIONS = ["NRT"]      # IATA codes for destination airports
DATE_RANGE_DAYS = 3         # how many days ahead to search (used when --date is not passed)
```

Save the file. No other file needs editing before first run.

---

## 8. Verify the setup (smoke test)

Run this to confirm Playwright can launch a browser and the imports resolve:

```bash
.venv/bin/python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('https://example.com', wait_until='networkidle')
    print('Browser OK — title:', page.title())
    b.close()
"
```

Expected output: `Browser OK — title: Example Domain`

If this fails with a permissions error on macOS, run:

```bash
xattr -cr .venv/lib/python*/site-packages/playwright/driver/node
```

---

## 9. Run the tool

**Search the next N days (DATE_RANGE_DAYS from config):**

```bash
.venv/bin/python3 alaska/run_alaska_search.py
```

**Search a specific date only:**

```bash
.venv/bin/python3 alaska/run_alaska_search.py --date 2026-09-16
```

Each search takes 30–90 seconds per route/date combination due to the headless browser load and the anti-detection delay (8–15s between requests).

---

## 10. Verify results were saved

```bash
sqlite3 output/alaska_awards.db "SELECT flight_date, flight_number, cabin, miles, taxes_usd, seats FROM alaska_awards ORDER BY miles LIMIT 20;"
```

If the table is empty after a run, it usually means the date searched had no award availability on that route — try a date 2–3 months out.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: playwright` | Wrong Python interpreter | Use `.venv/bin/python3`, not `python3` |
| `Executable doesn't exist` | Playwright browser not installed | Re-run step 5 |
| `fetch_flight_rows` returns `[]` | Bot detection or no availability | Try a date further out; run again after a few minutes |
| `sqlite3: no such table: alaska_awards` | DB not initialized yet | Run the tool once; `db.py` creates the table on first run |
| `SyntaxError: unsupported operand` | Python < 3.10 | Install Python 3.10+ (step 1) |

---

## Southwest Airlines — bot-detection fixes (Akamai)

Southwest protects its booking and calendar APIs with Akamai bot detection.
A plain headless Playwright session is reliably blocked, causing scrapers to
silently return no data even though the awards are visible in a real browser.
The following measures were discovered through trial and error and **must all
be applied together** — removing any one of them may cause silent failures.

### What was failing

The original scraper used `page.on("response", …)` + `wait_until="networkidle"`.
Akamai was serving a blocked/redirect page instead of the real SPA.  `networkidle`
fired on that blocked page (it is still "idle"), so the callback never saw the
target API URL and the scraper returned `None` / "no availability".

### Fix 1 — use `expect_response()` instead of a passive listener

Replace the `page.on("response", …)` + `networkidle` pattern with Playwright's
`page.expect_response()` context manager:

```python
with page.expect_response(
    lambda r: TARGET_URL_FRAGMENT in r.url and r.status == 200,
    timeout=90_000,
) as response_info:
    page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
raw = response_info.value.json()
```

**Why:** `expect_response` actively waits up to 90 s for a matching response
regardless of network idle state.  It also raises a `TimeoutError` if the API
never fires (visible in the logs), rather than silently returning nothing.
`wait_until="domcontentloaded"` is used instead of `"networkidle"` so the
`goto` does not prematurely resolve on the bot-blocked page.

### Fix 2 — suppress the `navigator.webdriver` flag

Inject a script into the page context *before* any page scripts run:

```python
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
"""
context.add_init_script(_STEALTH_JS)
```

**Why:** `navigator.webdriver === true` is the first signal Akamai checks.
`languages` and `plugins` being empty are secondary fingerprint checks also
used in the scoring.

### Fix 3 — pass `--disable-blink-features=AutomationControlled`

```python
browser = p.chromium.launch(
    headless=True,
    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
)
```

**Why:** This flag prevents Chrome from advertising its automation mode via the
`chrome.runtime` and `window.chrome` objects that Akamai also reads.

### Fix 4 — set a realistic browser context fingerprint

```python
context = browser.new_context(
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) "
               "Chrome/148.0.0.0 Safari/537.36",
    viewport={"width": 1440, "height": 900},
    locale="en-US",
    timezone_id="America/Los_Angeles",
    java_script_enabled=True,
)
```

**Why:** A missing or inconsistent viewport, locale, or timezone is a secondary
bot signal.  The UA string must match the version of Chromium that Playwright
actually downloads (check with `playwright --version`).

### All four fixes are implemented in `southwest/scraper.py` in `_make_context()`

If Southwest starts blocking again after a period of time, the most likely
causes in order are:

1. Akamai updated its fingerprint checks — extend `_STEALTH_JS` with additional
   property overrides (e.g. `navigator.hardwareConcurrency`, `screen.colorDepth`).
2. The Playwright Chromium version is outdated — run `playwright install chromium`
   to update.
3. The headless UA string no longer matches the installed Chromium — update the
   `user_agent` string in `_make_context()`.
4. Akamai added a JS challenge that requires interaction before the API fires —
   add a `page.wait_for_selector()` for a known UI element before the
   `expect_response` block.

