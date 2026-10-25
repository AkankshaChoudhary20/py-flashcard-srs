from datetime import date
from app.srs import SRSState, review

def test_finite_large_factor_does_not_overflow_before_date_cap():
    today = date(2026, 10, 25)
    result = review(SRSState(1e308, 100, 3), 4, today=today)
    assert result.due_date == date.max
    assert result.interval_days == (date.max - today).days
