"""
FastAPI app for the spaced-repetition flashcard service.

Run with:
    uvicorn app.main:app --reload

Serves a small JSON REST API plus a static, vanilla-JS single-page frontend
at "/".
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app import db
from app.srs import SRSState, grade_to_quality, review

app = FastAPI(title="Flashcard SRS")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DeckCreate(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class DeckOut(BaseModel):
    id: int
    name: str
    created_at: str


class CardCreate(BaseModel):
    front: str = Field(min_length=1)
    back: str = Field(min_length=1)

    @field_validator("front", "back", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class CardOut(BaseModel):
    id: int
    deck_id: int
    front: str
    back: str
    ease_factor: float
    interval_days: int
    repetitions: int
    due_date: str
    last_reviewed: Optional[str]
    created_at: str


class ReviewIn(BaseModel):
    card_id: int
    grade: Optional[str] = None
    quality: Optional[int] = None

    def resolve_quality(self) -> int:
        if self.quality is not None:
            if not 0 <= self.quality <= 5:
                raise HTTPException(400, "quality must be between 0 and 5")
            return self.quality
        if self.grade is not None:
            try:
                return grade_to_quality(self.grade)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
        raise HTTPException(400, "either 'grade' or 'quality' is required")


def _row_to_card(row) -> dict:
    return {
        "id": row["id"],
        "deck_id": row["deck_id"],
        "front": row["front"],
        "back": row["back"],
        "ease_factor": row["ease_factor"],
        "interval_days": row["interval_days"],
        "repetitions": row["repetitions"],
        "due_date": row["due_date"],
        "last_reviewed": row["last_reviewed"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Deck endpoints
# ---------------------------------------------------------------------------

@app.post("/api/decks", response_model=DeckOut)
def create_deck(payload: DeckCreate):
    with db.connect() as conn:
        row = db.create_deck(conn, payload.name)
        return dict(row)


@app.get("/api/decks", response_model=list[DeckOut])
def list_decks():
    with db.connect() as conn:
        return [dict(r) for r in db.list_decks(conn)]


# ---------------------------------------------------------------------------
# Card endpoints
# ---------------------------------------------------------------------------

@app.post("/api/decks/{deck_id}/cards", response_model=CardOut)
def add_card(deck_id: int, payload: CardCreate):
    with db.connect() as conn:
        if db.get_deck(conn, deck_id) is None:
            raise HTTPException(404, f"deck {deck_id} not found")
        row = db.create_card(conn, deck_id, payload.front, payload.back)
        return _row_to_card(row)


@app.get("/api/decks/{deck_id}/cards", response_model=list[CardOut])
def list_cards_in_deck(deck_id: int):
    with db.connect() as conn:
        if db.get_deck(conn, deck_id) is None:
            raise HTTPException(404, f"deck {deck_id} not found")
        return [_row_to_card(r) for r in db.list_cards(conn, deck_id)]


@app.get("/api/cards/due", response_model=list[CardOut])
def get_due_cards(deck_id: Optional[int] = None):
    """Due cards, optionally scoped to a single deck. Omit deck_id to get
    due cards across all decks."""
    with db.connect() as conn:
        if deck_id is not None and db.get_deck(conn, deck_id) is None:
            raise HTTPException(404, f"deck {deck_id} not found")
        return [_row_to_card(r) for r in db.get_due_cards(conn, deck_id)]


# ---------------------------------------------------------------------------
# Review endpoint
# ---------------------------------------------------------------------------

@app.post("/api/reviews", response_model=CardOut)
def submit_review(payload: ReviewIn):
    quality = payload.resolve_quality()
    with db.connect() as conn:
        card_row = db.get_card(conn, payload.card_id)
        if card_row is None:
            raise HTTPException(404, f"card {payload.card_id} not found")

        state = SRSState(
            ease_factor=card_row["ease_factor"],
            interval_days=card_row["interval_days"],
            repetitions=card_row["repetitions"],
        )
        result = review(state, quality, today=date.today())

        updated = db.update_card_srs(
            conn,
            card_id=payload.card_id,
            ease_factor=result.ease_factor,
            interval_days=result.interval_days,
            repetitions=result.repetitions,
            due_date=result.due_date,
        )
        return _row_to_card(updated)


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
