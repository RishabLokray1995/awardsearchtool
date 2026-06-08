from __future__ import annotations

import sys
import uuid
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from american import session

_API_URL = "https://www.aa.com/booking/api/search/calendar"

_BASE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US",
    "content-type": "application/json",
    "origin": "https://www.aa.com",
    "referer": "https://www.aa.com/booking/choose-flights/1",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "priority": "u=1, i",
}


def _build_body(origin: str, destination: str, date: str, cabin: str) -> dict:
    return {
        "metadata": {"selectedProducts": [], "tripType": "OneWay", "udo": {}},
        "passengers": [{"type": "adult", "count": 1}],
        "requestHeader": {"clientId": "AAcom"},
        "slices": [{
            "allCarriers": True,
            "cabin": cabin,
            "connectionCity": None,
            "departureDate": date,
            "destination": destination,
            "destinationNearbyAirports": False,
            "maxStops": "1",
            "origin": origin,
            "originNearbyAirports": False,
        }],
        "tripOptions": {
            "corporateBooking": False,
            "fareType": "Lowest",
            "locale": "en_US",
            "pointOfSale": "",
            "searchType": "Award",
            "enableBenefits": True,
        },
        "loyaltyInfo": None,
        "version": "",
        "queryParams": {
            "sliceIndex": 0, "sessionId": "", "solutionSet": "", "solutionId": "",
        },
    }


def fetch_calendar(
    origin: str,
    destination: str,
    date: str,
    cabin: str = "BUSINESS,FIRST",
) -> dict:
    """
    POST to the AA award calendar API using session credentials from
    config.py (AA_COOKIE_STRING / AA_XSRF_TOKEN).

    Raises:
        ValueError  : credentials are empty — see config.py instructions.
        requests.HTTPError : 403 means the session has expired; update config.py.
    """
    cookie_string, xsrf_token = session.load()

    if not cookie_string or not xsrf_token:
        raise ValueError(
            "\n\nAA credentials are not set. To fix:\n"
            "  1. Open https://www.aa.com in Chrome and run any award search.\n"
            "  2. DevTools → Network → filter 'calendar' → find the POST request.\n"
            "  3. Right-click → Copy → Copy as cURL.\n"
            "  4. Paste the -b '...' cookie string  → config.py  AA_COOKIE_STRING\n"
            "  5. Paste the x-xsrf-token value      → config.py  AA_XSRF_TOKEN\n"
        )

    cid = str(uuid.uuid4())
    headers = {
        **_BASE_HEADERS,
        "cookie": cookie_string,
        "x-xsrf-token": xsrf_token,
        "x-cid": cid,
        "baggage": f"clientId=AAcom,xcId={cid}",
    }

    try:
        resp = requests.post(
            _API_URL,
            json=_build_body(origin, destination, date, cabin),
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            raise requests.HTTPError(
                "\n\nAA session expired (HTTP 403). To fix:\n"
                "  1. Open https://www.aa.com in Chrome and run any award search.\n"
                "  2. DevTools → Network → filter 'calendar' → find the POST request.\n"
                "  3. Right-click → Copy → Copy as cURL.\n"
                "  4. Paste the -b '...' cookie string  → config.py  AA_COOKIE_STRING\n"
                "  5. Paste the x-xsrf-token value      → config.py  AA_XSRF_TOKEN\n",
                response=e.response,
            ) from e
        if e.response.status_code == 429:
            raise requests.HTTPError(
                "AA rate limit hit (HTTP 429) — wait a minute and try again.",
                response=e.response,
            ) from e
        raise

    return resp.json()
