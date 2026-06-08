"""
Southwest Airlines award-search response parser.

Converts the raw JSON returned by fetch_award_data() into a flat list of
award dicts that match the southwest_awards database schema.
"""

from __future__ import annotations

# Maps Southwest fare-family codes → human-readable cabin/tier labels
_FARE_FAMILY_TO_LABEL = {
    "WGARED": "wanna_get_away",
    "PLURED": "wanna_get_away_plus",
    "ANYRED": "anytime",
    "BUSRED": "business_select",
}


def parse_award_data(raw: dict) -> list[dict]:
    """
    Parse a Southwest shopping API response dict into a flat list of awards.

    Each dict contains:
        flight_number   str    e.g. "WN 3538"  (first flight number)
        departure_time  str    ISO-8601 departure datetime
        arrival_time    str    ISO-8601 arrival datetime
        carrier         str    always "WN"
        fare_type       str    "wanna_get_away" | "wanna_get_away_plus" |
                               "anytime" | "business_select"
        miles           int    Rapid Rewards points cost
        taxes_usd       float  cash taxes/fees in USD
        stops           int    number of intermediate stops
        duration_min    int    total itinerary duration in minutes
    """
    awards: list[dict] = []

    try:
        air_products = (
            raw.get("data", {})
               .get("searchResults", {})
               .get("airProducts", [])
        )
    except AttributeError:
        return awards

    for product in air_products:
        details = product.get("details") or []
        for detail in details:
            # Skip flights with no available fares
            filter_tags = detail.get("filterTags") or []
            if "AVAILABLE" not in filter_tags:
                continue

            flight_numbers = detail.get("flightNumbers") or []
            flight_number = f"WN {flight_numbers[0]}" if flight_numbers else "WN"

            departure_time = detail.get("departureDateTime", "")
            arrival_time = detail.get("arrivalDateTime", "")
            duration_min = int(detail.get("totalDuration") or 0)

            segments = detail.get("segments") or []
            stops = len(segments) - 1 if segments else 0

            fare_products = (
                detail.get("fareProducts", {})
                      .get("ADULT", {})
            )

            for fare_key, fare_label in _FARE_FAMILY_TO_LABEL.items():
                fare_info = fare_products.get(fare_key)
                if not fare_info:
                    continue
                if fare_info.get("availabilityStatus") != "AVAILABLE":
                    continue

                fare = fare_info.get("fare") or {}
                total_fare = fare.get("totalFare") or {}
                taxes_fees = fare.get("totalTaxesAndFees") or {}

                miles_raw = total_fare.get("value")
                if miles_raw is None:
                    continue

                awards.append(
                    {
                        "flight_number": flight_number,
                        "departure_time": departure_time,
                        "arrival_time": arrival_time,
                        "carrier": "WN",
                        "fare_type": fare_label,
                        "miles": int(miles_raw),
                        "taxes_usd": float(taxes_fees.get("value") or 0.0),
                        "stops": stops,
                        "duration_min": duration_min,
                    }
                )

    return awards


def parse_calendar_data(raw: dict) -> list[dict]:
    """
    Parse a Southwest Low Fare Calendar API response into a flat list of
    per-day award dicts.

    Each dict contains:
        date        str    "YYYY-MM-DD"
        fare_type   str    "wanna_get_away" | "wanna_get_away_plus" |
                           "anytime" | "business_select"
        miles       int    Rapid Rewards points cost
        taxes_usd   float  cash taxes/fees in USD
    """
    awards: list[dict] = []

    try:
        search_results = raw.get("data", {}).get("searchResults", [])
    except AttributeError:
        return awards

    for result in search_results:
        calendar_days = result.get("lowFareCalendarDays") or []
        for day in calendar_days:
            date_str = day.get("date", "")
            fares = day.get("fares") or {}

            for fare_key, fare_label in _FARE_FAMILY_TO_LABEL.items():
                fare_info = fares.get(fare_key)
                if not fare_info:
                    continue

                total_fare = fare_info.get("totalFare") or {}
                taxes_fees = fare_info.get("totalTaxesAndFees") or {}

                miles_raw = total_fare.get("value")
                if miles_raw is None:
                    continue

                awards.append(
                    {
                        "date": date_str,
                        "fare_type": fare_label,
                        "miles": int(miles_raw),
                        "taxes_usd": float(taxes_fees.get("value") or 0.0),
                    }
                )

    return awards


