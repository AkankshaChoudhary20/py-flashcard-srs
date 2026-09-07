"""Unit tests for the pure SM-2 implementation in app/srs.py."""
from datetime import date

import pytest

from app.srs import (
    DEFAULT_EASE_FACTOR,
    MIN_EASE_FACTOR,
    SRSState,
    grade_to_quality,
    review,
)

TODAY = date(2026, 1, 1)


def brand_new_card() -> SRSState:
    return SRSState(ease_factor=DEFAULT_EASE_FACTOR, interval_days=0, repetitions=0)


# ---------------------------------------------------------------------------
# First review of a brand new card
# ---------------------------------------------------------------------------

def test_first_review_good_sets_interval_to_one_day():
    result = review(brand_new_card(), quality=4, today=TODAY)
    assert result.repetitions == 1
    assert result.interval_days == 1
    assert result.due_date == date(2026, 1, 2)
    # EF' = 2.5 + (0.1 - (5-4)*(0.08 + (5-4)*0.02)) = 2.5 + (0.1 - 0.1) = 2.5
    assert result.ease_factor == pytest.approx(2.5)


def test_first_review_easy_increases_ease_factor():
    result = review(brand_new_card(), quality=5, today=TODAY)
    assert result.repetitions == 1
    assert result.interval_days == 1
    # EF' = 2.5 + (0.1 - 0*(0.08+0)) = 2.6
    assert result.ease_factor == pytest.approx(2.6)


def test_first_review_hard_decreases_ease_factor_but_still_passes():
    result = review(brand_new_card(), quality=3, today=TODAY)
    assert result.repetitions == 1
    assert result.interval_days == 1
    # EF' = 2.5 + (0.1 - 2*(0.08+2*0.02)) = 2.5 + (0.1-0.24) = 2.36
    assert result.ease_factor == pytest.approx(2.36)


# ---------------------------------------------------------------------------
# Consecutive "Good" reviews growing the interval
# ---------------------------------------------------------------------------

def test_second_consecutive_good_review_sets_interval_to_six_days():
    first = review(brand_new_card(), quality=4, today=TODAY)
    state_after_first = SRSState(
        ease_factor=first.ease_factor,
        interval_days=first.interval_days,
        repetitions=first.repetitions,
    )
    second = review(state_after_first, quality=4, today=date(2026, 1, 2))
    assert second.repetitions == 2
    assert second.interval_days == 6
    assert second.due_date == date(2026, 1, 8)


def test_third_consecutive_good_review_multiplies_interval_by_ease_factor():
    state = SRSState(ease_factor=DEFAULT_EASE_FACTOR, interval_days=0, repetitions=0)
    r1 = review(state, quality=4, today=TODAY)
    state = SRSState(r1.ease_factor, r1.interval_days, r1.repetitions)
    r2 = review(state, quality=4, today=TODAY)
    state = SRSState(r2.ease_factor, r2.interval_days, r2.repetitions)
    r3 = review(state, quality=4, today=TODAY)

    assert r3.repetitions == 3
    # interval = round(previous_interval(6) * ease_factor(2.5)) = 15
    assert r3.interval_days == round(6 * r2.ease_factor)
    assert r3.interval_days == 15


def test_many_consecutive_good_reviews_grow_interval_each_time():
    state = brand_new_card()
    today = TODAY
    intervals = []
    for _ in range(6):
        result = review(state, quality=4, today=today)
        intervals.append(result.interval_days)
        state = SRSState(result.ease_factor, result.interval_days, result.repetitions)
        today = result.due_date

    # Intervals should be non-decreasing and strictly growing after rep 2.
    assert intervals[0] == 1
    assert intervals[1] == 6
    for i in range(2, len(intervals)):
        assert intervals[i] > intervals[i - 1]


def test_easy_grades_grow_interval_faster_than_good_grades():
    state = brand_new_card()
    good_state = state
    easy_state = state
    for _ in range(3):
        g = review(good_state, quality=4, today=TODAY)
        good_state = SRSState(g.ease_factor, g.interval_days, g.repetitions)
        e = review(easy_state, quality=5, today=TODAY)
        easy_state = SRSState(e.ease_factor, e.interval_days, e.repetitions)

    assert easy_state.interval_days > good_state.interval_days
    assert easy_state.ease_factor > good_state.ease_factor


# ---------------------------------------------------------------------------
# A lapse resets interval/repetitions
# ---------------------------------------------------------------------------

def test_lapse_after_progress_resets_repetitions_and_interval():
    state = brand_new_card()
    for _ in range(3):
        r = review(state, quality=4, today=TODAY)
        state = SRSState(r.ease_factor, r.interval_days, r.repetitions)
    assert state.repetitions == 3
    assert state.interval_days > 1

    lapse = review(state, quality=0, today=TODAY)
    assert lapse.repetitions == 0
    assert lapse.interval_days == 1
    assert lapse.due_date == date(2026, 1, 2)


def test_lapse_still_updates_ease_factor_downward():
    state = SRSState(ease_factor=2.5, interval_days=6, repetitions=2)
    result = review(state, quality=0, today=TODAY)
    # EF' = 2.5 + (0.1 - 5*(0.08+5*0.02)) = 2.5 + (0.1 - 0.9) = 1.7
    assert result.ease_factor == pytest.approx(1.7)


def test_lapse_ease_factor_never_drops_below_minimum():
    # Start near the floor and lapse repeatedly with quality 0.
    state = SRSState(ease_factor=1.3, interval_days=10, repetitions=4)
    result = review(state, quality=0, today=TODAY)
    assert result.ease_factor >= MIN_EASE_FACTOR
    assert result.ease_factor == pytest.approx(MIN_EASE_FACTOR)


def test_quality_of_two_is_also_a_lapse():
    state = SRSState(ease_factor=2.5, interval_days=6, repetitions=2)
    result = review(state, quality=2, today=TODAY)
    assert result.repetitions == 0
    assert result.interval_days == 1


# ---------------------------------------------------------------------------
# Boundary quality values
# ---------------------------------------------------------------------------

def test_quality_zero_is_valid_and_is_a_lapse():
    result = review(brand_new_card(), quality=0, today=TODAY)
    assert result.repetitions == 0
    assert result.interval_days == 1


def test_quality_five_is_valid_and_maximizes_ease_factor_gain():
    result = review(brand_new_card(), quality=5, today=TODAY)
    assert result.ease_factor == pytest.approx(2.6)


def test_quality_three_is_the_lapse_boundary_and_still_passes():
    result = review(brand_new_card(), quality=3, today=TODAY)
    assert result.repetitions == 1  # quality 3 counts as a pass, not a lapse


def test_quality_below_zero_raises():
    with pytest.raises(ValueError):
        review(brand_new_card(), quality=-1, today=TODAY)


def test_quality_above_five_raises():
    with pytest.raises(ValueError):
        review(brand_new_card(), quality=6, today=TODAY)


# ---------------------------------------------------------------------------
# Ease factor never drops below the floor even across repeated hard reviews
# ---------------------------------------------------------------------------

def test_ease_factor_floor_enforced_across_repeated_hard_reviews():
    state = brand_new_card()
    for _ in range(20):
        r = review(state, quality=3, today=TODAY)
        assert r.ease_factor >= MIN_EASE_FACTOR
        state = SRSState(r.ease_factor, r.interval_days, r.repetitions)


# ---------------------------------------------------------------------------
# grade_to_quality helper (Again/Hard/Good/Easy button mapping)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "grade,expected",
    [
        ("again", 0),
        ("Again", 0),
        ("hard", 3),
        ("HARD", 3),
        ("good", 4),
        ("easy", 5),
        (" Easy ", 5),
    ],
)
def test_grade_to_quality_mapping(grade, expected):
    assert grade_to_quality(grade) == expected


def test_grade_to_quality_rejects_unknown_grade():
    with pytest.raises(ValueError):
        grade_to_quality("meh")


# ---------------------------------------------------------------------------
# due_date computation
# ---------------------------------------------------------------------------

def test_due_date_defaults_to_today_when_not_given():
    result = review(brand_new_card(), quality=4)
    assert result.due_date == date.today().fromordinal(date.today().toordinal() + 1)
