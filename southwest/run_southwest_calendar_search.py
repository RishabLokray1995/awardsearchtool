from __future__ import annotations

import argparse
import itertools
import random
import sys
import time
from pathlib import Path

# Make the project root importable regardless of where the script is invoked from
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from southwest.parser import parse_calendar_data
from southwest.scraper import fetch_calendar_data
from db import init_southwest_db, insert_southwest_calendar_awards


def run(month: str | None = None) -> None:
    """
    Search Southwest Low Fare Calendar for each origin/destination pair.

    Each API call returns a full month of per-day lowest fares (all 4 fare
    tiers), so this is much faster than the per-day flight search.

    month: "YYYY-MM-01" (first of the target month).  Omit to iterate over
           all months defined by SOUTHWEST_SEARCH_MONTHS in config.
    """
    conn = init_southwest_db(config.SOUTHWEST_DB_PATH)
    month_starts = [month] if month else config.get_southwest_month_starts()

    combinations = list(itertools.product(config.ORIGINS, config.DESTINATIONS, month_starts))
    total = len(combinations)
    print(
        f"Running {total} calendar searches  "
        f"({len(config.ORIGINS)} origins × {len(config.DESTINATIONS)} destinations "
        f"× {len(month_starts)} months)\n"
    )

    for i, (origin, destination, month_start) in enumerate(combinations, 1):
        label = f"[{i}/{total}] {origin}→{destination} {month_start[:7]}"
        try:
            raw = fetch_calendar_data(origin, destination, month_start)
            if raw is None:
                print(f"  {label}  →  no API response captured")
                continue

            awards = parse_calendar_data(raw)
            insert_southwest_calendar_awards(conn, awards, origin, destination)

            if awards:
                wga_awards = [a for a in awards if a["fare_type"] == "wanna_get_away"]
                best = min(wga_awards or awards, key=lambda a: a["miles"])
                days = len({a["date"] for a in awards})
                print(
                    f"  {label}  →  {days} days with availability "
                    f"(best WGA: {best['miles']:,} pts on {best['date']})"
                )
            else:
                print(f"  {label}  →  no availability")

        except Exception as e:
            import traceback
            print(f"  {label}  →  ERROR: {e}")
            traceback.print_exc()

        if i < total:
            time.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))

    conn.close()
    print(f"\nDone. Results in {config.SOUTHWEST_DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Southwest Airlines Low Fare Calendar award search"
    )
    parser.add_argument(
        "--month",
        metavar="YYYY-MM-01",
        help=(
            "Search only this month (use the first of the month, e.g. 2026-08-01). "
            "Omit to use SOUTHWEST_SEARCH_MONTHS from config."
        ),
    )
    args = parser.parse_args()
    run(month=args.month)

