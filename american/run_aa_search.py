from __future__ import annotations

import argparse
import itertools
import random
import sys
import time
import warnings
from pathlib import Path

# Suppress the LibreSSL/urllib3 warning on macOS system Python
warnings.filterwarnings("ignore", message=".*LibreSSL.*")
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")

# Make the project root importable regardless of where the script is invoked from
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from american.parser import parse_calendar_awards
from american.scraper import fetch_calendar
from db import init_aa_db, insert_aa_awards


def run(date: str | None = None) -> None:
    conn = init_aa_db(config.AA_DB_PATH)

    # AA calendar API returns the whole month in one call.
    # If a specific date is given, use the 1st of that month.
    # Otherwise search AA_SEARCH_MONTHS calendar months.
    if date:
        month_starts = [date[:7] + "-01"]   # e.g. "2026-06-19" → "2026-06-01"
    else:
        month_starts = config.get_aa_month_starts()

    combinations = list(itertools.product(config.ORIGINS, config.DESTINATIONS, month_starts))
    total = len(combinations)
    print(
        f"Running {total} AA calendar searches  "
        f"({len(config.ORIGINS)} origins × {len(config.DESTINATIONS)} destinations "
        f"× {len(month_starts)} month(s))\n"
    )

    for i, (origin, destination, flight_date) in enumerate(combinations, 1):
        label = f"[{i}/{total}] {origin}→{destination} month of {flight_date[:7]}"
        try:
            data = fetch_calendar(origin, destination, flight_date, cabin=config.AA_CABIN)
            awards = parse_calendar_awards(data)
            insert_aa_awards(conn, awards, origin, destination)

            if awards:
                best = min(awards, key=lambda a: a["miles"] or float("inf"))
                print(
                    f"  {label}  →  {len(awards)} days with availability "
                    f"(best: {best['miles']:,} miles / ${best['taxes_usd']} taxes "
                    f"on {best['date']})"
                )
            else:
                print(f"  {label}  →  no availability")

        except Exception as e:
            print(f"  {label}  →  ERROR: {e}")

        if i < total:
            time.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))

    conn.close()
    print(f"\nDone. Results in {config.AA_DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search American Airlines award availability via the calendar API."
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Search the month containing this date (e.g. 2026-06-19 searches all of June). "
             "Omit to use AA_SEARCH_MONTHS from config.",
    )
    args = parser.parse_args()
    run(date=args.date)
