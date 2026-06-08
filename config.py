from datetime import date, timedelta

# --- Search Matrix ---
ORIGINS = ["SEA"]
DESTINATIONS = ["NRT"]   # example: Seattle → Tokyo
DATE_RANGE_DAYS = 3           # search the next N days starting today

# --- Output ---
DB_PATH = "output/awards.db"

# Delay range (seconds) between page loads to avoid bot detection
DELAY_MIN = 8
DELAY_MAX = 15


def get_date_range() -> list[str]:
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(DATE_RANGE_DAYS)]
