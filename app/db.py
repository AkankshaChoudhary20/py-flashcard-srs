"""
SQLite storage layer (stdlib sqlite3, no ORM).

Schema:
    deck(id, name, created_at)
    card(id, deck_id, front, back,
         ease_factor, interval_days, repetitions,
         due_date, last_reviewed, created_at)
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

from app.srs import DEFAULT_EASE_FACTOR

DB_PATH = Path(__file__).resolve().parent.parent / "flashcards.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS deck (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS card (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL REFERENCES deck(id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions INTEGER NOT NULL DEFAULT 0,
    due_date TEXT NOT NULL,
    last_reviewed TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_card_deck_id ON card(deck_id);
CREATE INDEX IF NOT EXISTS idx_card_due_date ON card(due_date);
"""


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def connect(db_path: Path | str = DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Deck operations
# ---------------------------------------------------------------------------

def create_deck(conn: sqlite3.Connection, name: str) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO deck (name, created_at) VALUES (?, ?)",
        (name, datetime.utcnow().isoformat()),
    )
    conn.commit()
    return get_deck(conn, cur.lastrowid)


def get_deck(conn: sqlite3.Connection, deck_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM deck WHERE id = ?", (deck_id,)).fetchone()


def list_decks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM deck ORDER BY id").fetchall()


# ---------------------------------------------------------------------------
# Card operations
# ---------------------------------------------------------------------------

def create_card(
    conn: sqlite3.Connection, deck_id: int, front: str, back: str
) -> sqlite3.Row:
    now = datetime.utcnow().isoformat()
    today = date.today().isoformat()
    cur = conn.execute(
        """
        INSERT INTO card
            (deck_id, front, back, ease_factor, interval_days, repetitions,
             due_date, last_reviewed, created_at)
        VALUES (?, ?, ?, ?, 0, 0, ?, NULL, ?)
        """,
        (deck_id, front, back, DEFAULT_EASE_FACTOR, today, now),
    )
    conn.commit()
    return get_card(conn, cur.lastrowid)


def get_card(conn: sqlite3.Connection, card_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM card WHERE id = ?", (card_id,)).fetchone()


def list_cards(conn: sqlite3.Connection, deck_id: Optional[int] = None) -> list[sqlite3.Row]:
    if deck_id is None:
        return conn.execute("SELECT * FROM card ORDER BY id").fetchall()
    return conn.execute(
        "SELECT * FROM card WHERE deck_id = ? ORDER BY id", (deck_id,)
    ).fetchall()


def get_due_cards(
    conn: sqlite3.Connection, deck_id: Optional[int] = None, on: Optional[date] = None
) -> list[sqlite3.Row]:
    """Cards whose due_date is today or earlier. If deck_id is None, cards
    across all decks are returned."""
    today = (on or date.today()).isoformat()
    if deck_id is None:
        return conn.execute(
            "SELECT * FROM card WHERE due_date <= ? ORDER BY due_date", (today,)
        ).fetchall()
    return conn.execute(
        "SELECT * FROM card WHERE deck_id = ? AND due_date <= ? ORDER BY due_date",
        (deck_id, today),
    ).fetchall()


def update_card_srs(
    conn: sqlite3.Connection,
    card_id: int,
    ease_factor: float,
    interval_days: int,
    repetitions: int,
    due_date: date,
    reviewed_at: Optional[datetime] = None,
) -> sqlite3.Row:
    reviewed_at = reviewed_at or datetime.utcnow()
    conn.execute(
        """
        UPDATE card
        SET ease_factor = ?, interval_days = ?, repetitions = ?,
            due_date = ?, last_reviewed = ?
        WHERE id = ?
        """,
        (
            ease_factor,
            interval_days,
            repetitions,
            due_date.isoformat(),
            reviewed_at.isoformat(),
            card_id,
        ),
    )
    conn.commit()
    return get_card(conn, card_id)
