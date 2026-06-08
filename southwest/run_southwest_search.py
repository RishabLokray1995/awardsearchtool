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
from southwest.parser import parse_award_data
from southwest.scraper import fetch_award_data
from db import init_southwest_db, insert_southwest_awards


def run(date: str | None = None) -> None:
    conn = init_southwest_db(config.SOUTHWEST_DB_PATH)
    dates = [date] if date else config.get_date_range()

    combinations = list(itertools.product(config.ORIGINS, config.DESTINATIONS, dates))
    total = len(combinations)
    print(
        f"Running {total} searches  "
        f"({len(config.ORIGINS)} origins × {len(config.DESTINATIONS)} destinations "
        f"× {len(dates)} dates)\n"
    )

    for i, (origin, destination, flight_date) in enumerate(combinations, 1):
        label = f"[{i}/{total}] {origin}→{destination} {flight_date}"
        try:
            raw = fetch_award_data(origin, destination, flight_date)
            if raw is None:
                print(f"  {label}  →  no API response captured")
                continue

            awards = parse_award_data(raw)
            insert_southwest_awards(conn, awards, origin, destination, flight_date)

            if awards:
                best = min(awards, key=lambda a: a["miles"])
                print(
                    f"  {label}  →  {len(awards)} awards "
                    f"(best: {best['miles']:,} pts / {best['fare_type']})"
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
    parser = argparse.ArgumentParser(description="Southwest Airlines award search")
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Search only this date. Omit to use DATE_RANGE_DAYS from config.",
    )
    args = parser.parse_args()
    run(date=args.date)

