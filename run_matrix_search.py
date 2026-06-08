import itertools
import random
import time

import config
from alaska.parser import parse_award_data
from alaska.scraper import fetch_flight_rows
from db import init_db, insert_awards


def run() -> None:
    conn = init_db(config.DB_PATH)
    dates = config.get_date_range()

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
            rows = fetch_flight_rows(origin, destination, flight_date)
            awards = parse_award_data(rows)
            insert_awards(conn, awards, origin, destination, flight_date)

            if awards:
                best = min(awards, key=lambda a: a["miles"])
                print(
                    f"  {label}  →  {len(awards)} awards "
                    f"(best: {best['miles']:,} miles / {best['cabin']})"
                )
            else:
                print(f"  {label}  →  no availability")

        except Exception as e:
            print(f"  {label}  →  ERROR: {e}")

        if i < total:
            time.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))

    conn.close()
    print(f"\nDone. Results in {config.DB_PATH}")


if __name__ == "__main__":
    run()
