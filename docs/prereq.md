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
