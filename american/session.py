"""
AA session management and search-page navigation.
Credentials are read directly from config.py (AA_COOKIE_STRING / AA_XSRF_TOKEN).
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

import requests as _requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

_SEARCH_HEADERS = {
    "accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "priority": "u=0, i",
    "referer": "https://www.aa.com/homePage.do",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
}


def load() -> tuple[str, str]:
    """Return (cookie_string, xsrf_token) from config.py."""
    return config.AA_COOKIE_STRING, config.AA_XSRF_TOKEN


def build_search_url(origin: str, destination: str, date: str) -> str:
    """
    Build the /booking/search GET URL — mirrors what the browser sends when you
    click 'Search' on the AA homepage for a one-way award search.
    """
    slices = json.dumps([{
        "orig": origin, "origNearby": False,
        "dest": destination, "destNearby": False,
        "date": date,
    }], separators=(",", ":"))
    qs = urllib.parse.urlencode({
        "locale": "en_US", "pax": "1", "adult": "1",
        "type": "OneWay", "searchType": "Award",
        "cabin": "", "carriers": "ALL", "travelType": "personal",
        "slices": slices,
    })
    return f"https://www.aa.com/booking/search?{qs}"


def navigate_to_search(
    origin: str,
    destination: str,
    date: str,
    verbose: bool = True,
) -> tuple[str, str]:
    """
    Make a GET request to /booking/search (exactly like a browser clicking Search).

    This serves two purposes:
      1. Verifies the current credentials are still valid.
      2. Captures any fresh Set-Cookie headers from the server and merges them
         into the session cache, extending the session lifetime.

    Returns:
        (cookie_string, xsrf_token) — the updated credentials.

    Raises:
        ValueError       : no credentials configured.
        requests.HTTPError : 403 = expired, 429 = rate limited.
    """
    cookie_string, xsrf_token = load()
    if not cookie_string or not xsrf_token:
        raise ValueError(
            "\n\nAA credentials are not set. See config.py for instructions."
        )

    url = build_search_url(origin, destination, date)
    headers = {**_SEARCH_HEADERS, "cookie": cookie_string}

    resp = _requests.get(url, headers=headers, allow_redirects=True, timeout=30)

    if resp.status_code == 403:
        raise _requests.HTTPError(
            "\n\nAA session expired (HTTP 403). Refresh credentials in config.py.",
            response=resp,
        )
    if resp.status_code == 429:
        raise _requests.HTTPError(
            "AA rate limit (HTTP 429) — wait a minute and retry.",
            response=resp,
        )
    resp.raise_for_status()

    # Merge any new cookies from the response into the existing cookie string
    if resp.cookies and verbose:
        print(f"  [session] Server returned {len(resp.cookies)} updated cookie(s)")

    if verbose:
        print(f"  [session] Landed on: {resp.url}")

    return cookie_string, xsrf_token
