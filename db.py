import sqlite3
from datetime import datetime, timezone
from pathlib import Path


CREATE_ALASKA_TABLE = """
CREATE TABLE IF NOT EXISTS alaska_awards (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    searched_at     TEXT NOT NULL,
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    flight_date     TEXT NOT NULL,
    flight_number   TEXT,
    departure_time  TEXT,
    arrival_time    TEXT,
    carrier         TEXT,
    cabin           TEXT,
    miles           INTEGER,
    taxes_usd       REAL,
    seats           INTEGER,
    stops           INTEGER
);
"""


CREATE_AA_TABLE = """
CREATE TABLE IF NOT EXISTS aa_awards (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    searched_at     TEXT NOT NULL,
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    flight_date     TEXT NOT NULL,
    miles           INTEGER,
    taxes_usd       REAL,
    lowest_price    INTEGER DEFAULT 0
);
"""


def init_alaska_db(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(CREATE_ALASKA_TABLE)
    conn.commit()
    return conn


def init_aa_db(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(CREATE_AA_TABLE)
    conn.commit()
    return conn


def insert_alaska_awards(
    conn: sqlite3.Connection,
    awards: list[dict],
    origin: str,
    destination: str,
    flight_date: str,
) -> None:
    if not awards:
        return
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            now,
            origin,
            destination,
            flight_date,
            a.get("flight_number"),
            a.get("departure_time"),
            a.get("arrival_time"),
            a.get("carrier"),
            a.get("cabin"),
            a.get("miles"),
            a.get("taxes_usd"),
            a.get("seats"),
            a.get("stops"),
        )
        for a in awards
    ]
    conn.executemany(
        """
        INSERT INTO alaska_awards
            (searched_at, origin, destination, flight_date, flight_number,
             departure_time, arrival_time, carrier, cabin, miles, taxes_usd,
             seats, stops)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def insert_aa_awards(
    conn: sqlite3.Connection,
    awards: list[dict],
    origin: str,
    destination: str,
) -> None:
    if not awards:
        return
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            now,
            origin,
            destination,
            a["date"],
            a.get("miles"),
            a.get("taxes_usd"),
            1 if a.get("lowest_price") else 0,
        )
        for a in awards
    ]
    conn.executemany(
        """
        INSERT INTO aa_awards
            (searched_at, origin, destination, flight_date, miles, taxes_usd, lowest_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
