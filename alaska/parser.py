_SOLUTION_TO_CABIN = {
    "REFUNDABLE_MAIN": "coach",
    "REFUNDABLE_BUSINESS": "business",
    "REFUNDABLE_PARTNER_PREMIUM": "premium",
}


def parse_award_data(rows: list[dict]) -> list[dict]:
    """
    Convert Alaska's dehydrated 'rows' list into a flat list of award dicts.

    Each dict:
        flight_number   str    "AS 505" (first segment's publishing carrier)
        departure_time  str    ISO-8601 from first segment
        arrival_time    str    ISO-8601 from last segment
        carrier         str    first segment carrier code e.g. "AS"
        cabin           str    "coach" | "business" | "premium"
        miles           int    atmosPoints cost
        taxes_usd       float  grandTotal cash fees in USD
        seats           int    seatsRemaining
        stops           int    number of connections (segments - 1)
    """
    awards: list[dict] = []

    for row in rows:
        segments = row.get("segments") or []
        if not segments:
            continue

        first = segments[0]
        last = segments[-1]

        carrier_info = first.get("publishingCarrier") or {}
        carrier_code = carrier_info.get("carrierCode", "")
        flight_num = carrier_info.get("flightNumber", "")
        flight_number = f"{carrier_code} {flight_num}".strip()

        departure_time = first.get("departureTime", "")
        arrival_time = last.get("arrivalTime", "")
        stops = len(segments) - 1

        for solution_key, cabin_label in _SOLUTION_TO_CABIN.items():
            sol = (row.get("solutions") or {}).get(solution_key)
            if sol is None:
                continue
            miles = sol.get("atmosPoints")
            if miles is None:
                continue
            awards.append(
                {
                    "flight_number": flight_number,
                    "departure_time": departure_time,
                    "arrival_time": arrival_time,
                    "carrier": carrier_code,
                    "cabin": cabin_label,
                    "miles": int(miles),
                    "taxes_usd": float(sol.get("grandTotal") or 0.0),
                    "seats": int(sol.get("seatsRemaining") or 0),
                    "stops": stops,
                }
            )

    return awards
