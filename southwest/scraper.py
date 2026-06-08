"""
Southwest Airlines award-search scraper.

Uses a headless Playwright browser to navigate to Southwest's booking page and
intercepts the internal JSON API call that returns award pricing data.  Because
Southwest's front-end uses dynamically generated anti-bot headers (Akamai
ee30zvqlwf-*), we let the real browser generate those headers and simply
capture the XHR response rather than replaying the request ourselves.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

_SHOPPING_URL_FRAGMENT = "/api/air-booking/v1/air-booking/page/air/booking/shopping"
_CALENDAR_URL_FRAGMENT = "/api/air-booking/v1/air-booking/page/air/low-fare-calendar/select-dates"
_SEARCH_PAGE_BASE = "https://www.southwest.com/air/booking/select-depart.html"
_CALENDAR_PAGE_BASE = "https://www.southwest.com/air/low-fare-calendar/select-dates"

# Injected into every page before any scripts run to suppress headless signals
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
"""


def _make_context(p):
    """Return a browser + context pair with stealth settings."""
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/148.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 900},
        locale="en-US",
        timezone_id="America/Los_Angeles",
        java_script_enabled=True,
    )
    context.add_init_script(_STEALTH_JS)
    return browser, context


def build_search_url(origin: str, destination: str, date: str) -> str:
    """date format: YYYY-MM-DD"""
    params = (
        f"adultsCount=1&adultPassengersCount=1"
        f"&originationAirportCode={origin}"
        f"&destinationAirportCode={destination}"
        f"&departureDate={date}"
        f"&departureTimeOfDay=ALL_DAY"
        f"&fareType=POINTS"
        f"&int=HOMEQBOMAIR"
        f"&passengerType=ADULT"
        f"&promoCode="
        f"&returnDate="
        f"&returnTimeOfDay=ALL_DAY"
        f"&tripType=oneway"
    )
    return f"{_SEARCH_PAGE_BASE}?{params}"


def build_calendar_url(origin: str, destination: str, month_start: str) -> str:
    """month_start format: YYYY-MM-01 (first day of the target month)"""
    params = (
        f"adultsCount=1&adultPassengersCount=1"
        f"&originationAirportCode={origin}"
        f"&destinationAirportCode={destination}"
        f"&departureDate={month_start}"
        f"&currencyCode=POINTS"
        f"&hasNearByAirport=false"
        f"&lapInfantPassengersCount=0"
        f"&passengerType=ADULT"
        f"&promoCode="
        f"&returnAirportCode="
        f"&returnDate="
        f"&selectedFlight1={month_start}"
        f"&selectedFlight2="
        f"&tripType=oneway"
    )
    return f"{_CALENDAR_PAGE_BASE}?{params}"


def fetch_award_data(origin: str, destination: str, date: str) -> dict | None:
    """
    Navigate to the Southwest award search page with a headless browser,
    intercept the internal shopping API call, and return the parsed JSON body.

    Returns None if no matching API response is captured before timeout.
    """
    page_url = build_search_url(origin, destination, date)

    with sync_playwright() as p:
        browser, context = _make_context(p)
        page = context.new_page()
        try:
            with page.expect_response(
                lambda r: _SHOPPING_URL_FRAGMENT in r.url and r.status == 200,
                timeout=90_000,
            ) as response_info:
                page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            return response_info.value.json()
        except Exception:
            return None
        finally:
            browser.close()


def fetch_calendar_data(origin: str, destination: str, month_start: str) -> dict | None:
    """
    Navigate to the Southwest Low Fare Calendar page and intercept the internal
    calendar API call.  Returns the full month's per-day fare data as a dict,
    or None if the API response is not captured before timeout.

    month_start: first day of the target month, e.g. "2026-08-01"
    """
    page_url = build_calendar_url(origin, destination, month_start)

    with sync_playwright() as p:
        browser, context = _make_context(p)
        page = context.new_page()
        try:
            with page.expect_response(
                lambda r: _CALENDAR_URL_FRAGMENT in r.url and r.status == 200,
                timeout=90_000,
            ) as response_info:
                page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            return response_info.value.json()
        except Exception:
            return None
        finally:
            browser.close()
