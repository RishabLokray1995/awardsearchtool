"""
Navigate to the AA award search page using credentials from config.py.

This mirrors exactly what a browser does when you click "Search" on aa.com —
a GET request to /booking/search that creates a real server session and redirects
to the choose-flights results page.

Use this to:
  • Verify your credentials in config.py are still valid.
  • Refresh/extend the session cache (output/aa_session.json) before a long run.

Usage:
    python american/run_aa_open_search.py --date 2026-06-19
    python american/run_aa_open_search.py  # uses DATE_RANGE_DAYS from config
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*LibreSSL.*")
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from american import session


def run(date: str | None = None) -> None:
    dates = [date] if date else config.get_date_range()

    for origin in config.ORIGINS:
        for destination in config.DESTINATIONS:
            for d in dates:
                label = f"{origin}→{destination} {d}"
                print(f"  Navigating: {label}")
                try:
                    session.navigate_to_search(origin, destination, d, verbose=True)
                    print(f"  ✓ {label}  — session valid\n")
                except Exception as e:
                    print(f"  ✗ {label}  — {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hit the AA /booking/search page to verify/refresh session credentials."
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Search a specific date. Omit to use DATE_RANGE_DAYS from config.",
    )
    args = parser.parse_args()
    run(date=args.date)

