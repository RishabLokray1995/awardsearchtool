from __future__ import annotations


def parse_calendar_awards(data: dict) -> list[dict]:
    """
    Flatten the AA calendar API response into a list of per-day award dicts.

    Each returned dict contains:
        date        (str)   YYYY-MM-DD
        miles       (int)   AAdvantage miles per passenger
        taxes_usd   (float) Cash co-pay in USD
        lowest_price (bool) True if this day is flagged as the month's lowest

    Days without availability (validDay=False or solution=None) are omitted.
    """
    awards: list[dict] = []

    for month in data.get("calendarMonths", []):
        for week in month.get("weeks", []):
            for day in week.get("days", []):
                if not day.get("validDay") or day.get("solution") is None:
                    continue

                solution = day["solution"]
                slices = solution.get("calendarSlices") or []
                lowest = slices[0].get("lowestPrice", False) if slices else False

                awards.append(
                    {
                        "date": day["date"],
                        "miles": solution.get("perPassengerAwardPoints"),
                        "taxes_usd": (
                            solution.get("perPassengerSaleTotal") or {}
                        ).get("amount"),
                        "lowest_price": lowest,
                    }
                )

    return awards

