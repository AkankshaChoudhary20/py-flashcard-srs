# Flashcard SRS

A small spaced-repetition flashcard app (like Anki), implementing the
SM-2 scheduling algorithm.

- **Backend:** FastAPI + Uvicorn
- **Storage:** SQLite via the stdlib `sqlite3` module (no ORM)
- **Frontend:** a single static HTML page with vanilla JS/CSS, served by
  FastAPI (no build step, no npm)

## Project layout

```
app/
  main.py          FastAPI app + REST endpoints, mounts the static frontend
  srs.py           Pure, unit-testable SM-2 algorithm
  db.py            SQLite schema + data access helpers (stdlib sqlite3)
  static/
    index.html     Frontend: deck management + study view
tests/
  test_srs.py      Unit tests for the SM-2 algorithm
requirements.txt
```

## Setup

```bash
cd py-flashcard-srs
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/** in a browser. A SQLite database file
(`flashcards.db`) is created automatically in the project root on first run.

## Run the tests

```bash
source .venv/bin/activate
pytest
```

## Using the app

1. Go to the **Decks** tab, create a deck, then click "Add card" on that
   deck to add front/back cards to it.
2. Go to the **Study** tab, optionally pick a deck from the dropdown (or
   leave it on "All decks"), and click "Show answer" to reveal the back of
   the current due card.
3. Grade your recall with **Again / Hard / Good / Easy**. This submits a
   review, updates the card's SM-2 state (ease factor, interval,
   repetitions, due date), and moves to the next due card.

## REST API

| Method | Path                        | Description                                  |
|--------|-----------------------------|-----------------------------------------------|
| POST   | `/api/decks`                | Create a deck (`{"name": "..."}`)             |
| GET    | `/api/decks`                | List all decks                                |
| POST   | `/api/decks/{deck_id}/cards`| Add a card to a deck (`{"front", "back"}`)    |
| GET    | `/api/decks/{deck_id}/cards`| List all cards in a deck                      |
| GET    | `/api/cards/due`            | Due cards across all decks                    |
| GET    | `/api/cards/due?deck_id=N`  | Due cards for a single deck                   |
| POST   | `/api/reviews`              | Submit a review (`{"card_id", "grade"}`)      |

`grade` is one of `again` / `hard` / `good` / `easy` (mapped internally to
SM-2 quality scores 0 / 3 / 4 / 5). You can alternatively pass a raw
`"quality"` integer (0-5) instead of `grade`.

Interactive API docs (Swagger UI) are available at `/docs` while the server
is running.

Deck names and card text are trimmed before storage. Empty or whitespace-only
values return HTTP `422`; internal line breaks in cards are preserved.

## The SM-2 algorithm

Implemented as a pure function `review(state, quality, today)` in
`app/srs.py`, so it has no dependency on FastAPI, SQLite, or wall-clock time
(a `today` date can be injected), which makes it straightforward to unit
test.

Rules:

- **Quality < 3 (a "lapse"):** `repetitions` resets to 0 and `interval_days`
  resets to 1. The ease factor is still recalculated (and can decrease) but
  is never allowed to drop below `1.3`.
- **Quality >= 3 (a pass):** `repetitions` increments by 1, and the new
  interval depends on the new repetition count:
  - 1st repetition → 1 day
  - 2nd repetition → 6 days
  - 3rd+ repetition → `round(previous_interval * new_ease_factor)`
- **Ease factor update** (standard SM-2 formula):
  `EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))`, clamped to a
  minimum of `1.3`.

See `tests/test_srs.py` for scenarios covering first reviews, consecutive
"Good" reviews growing the interval, a lapse resetting progress, and
boundary quality values (0, 3, 5, and out-of-range).

Raw review quality must be a JSON integer; strings, booleans, and decimal values return HTTP `422` without changing the card.
