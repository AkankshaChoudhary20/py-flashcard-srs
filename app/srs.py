"""
Core SM-2 spaced-repetition algorithm.

This module is intentionally free of any FastAPI / DB / IO concerns so that
it can be unit tested in isolation. `review()` is a pure function: given the
current SRS state of a card and a quality grade for the just-completed
review, it returns the new SRS state.

Quality grades (mirrors the classic SuperMemo-2 0-5 scale, simplified to the
four buttons a study UI typically exposes):

    Again -> 0
    Hard  -> 3
    Good  -> 4
    Easy  -> 5

Standard SM-2 rules:
    - If quality < 3: the review is a "lapse". repetitions resets to 0,
      interval resets to 1 day. ease_factor is still updated (it can still
      decrease) but is never allowed to drop below 1.3.
    - If quality >= 3: repetitions increments by 1, and the new interval is
      computed based on the new repetition count:
          repetitions == 1 -> interval = 1 day
          repetitions == 2 -> interval = 6 days
          repetitions >  2 -> interval = ceil(previous_interval * previous_ease_factor)
      ease_factor is updated using the SM-2 formula:
          EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
      and is clamped to a minimum of 1.3.
"""
from __future__ import annotations

from math import ceil
from dataclasses import dataclass
from datetime import date, timedelta

# Buttons -> SM-2 quality grades.
GRADE_TO_QUALITY = {
    "again": 0,
    "hard": 3,
    "good": 4,
    "easy": 5,
}

MIN_EASE_FACTOR = 1.3
DEFAULT_EASE_FACTOR = 2.5


@dataclass(frozen=True)
class SRSState:
    """The SRS state of a card, independent of any storage layer."""

    ease_factor: float
    interval_days: int
    repetitions: int


@dataclass(frozen=True)
class ReviewResult:
    """The outcome of applying one review to an SRSState."""

    ease_factor: float
    interval_days: int
    repetitions: int
    due_date: date


def _clamp_ease_factor(ef: float) -> float:
    return max(MIN_EASE_FACTOR, ef)


def _new_ease_factor(ef: float, quality: int) -> float:
    updated = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return round(_clamp_ease_factor(updated), 4)


def review(state: SRSState, quality: int, today: date | None = None) -> ReviewResult:
    """Apply a single SM-2 review step.

    Args:
        state: current SRS state of the card (before this review).
        quality: 0-5 quality grade for this review (see GRADE_TO_QUALITY for
            the mapping used by the Again/Hard/Good/Easy UI buttons).
        today: the date the review happens on (defaults to date.today()).
            Exposed as a parameter so tests are deterministic.

    Returns:
        ReviewResult with the new ease_factor, interval_days, repetitions,
        and due_date.
    """
    if not 0 <= quality <= 5:
        raise ValueError(f"quality must be between 0 and 5, got {quality}")

    if today is None:
        today = date.today()

    new_ef = _new_ease_factor(state.ease_factor, quality)

    if quality < 3:
        # Lapse: start the learning process over.
        new_repetitions = 0
        new_interval = 1
    else:
        new_repetitions = state.repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            # Schedule with the previously stored factor; this review's new
            # factor affects future repetitions. Fractional days round up.
            new_interval = max(1, ceil(state.interval_days * state.ease_factor))

    due_date = today + timedelta(days=new_interval)

    return ReviewResult(
        ease_factor=new_ef,
        interval_days=new_interval,
        repetitions=new_repetitions,
        due_date=due_date,
    )


def grade_to_quality(grade: str) -> int:
    """Map an Again/Hard/Good/Easy button label (case-insensitive) to a
    0-5 SM-2 quality score."""
    key = grade.strip().lower()
    if key not in GRADE_TO_QUALITY:
        raise ValueError(
            f"unknown grade {grade!r}; expected one of {sorted(GRADE_TO_QUALITY)}"
        )
    return GRADE_TO_QUALITY[key]
