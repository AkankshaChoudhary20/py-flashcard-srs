from datetime import date, datetime
import pytest
from app.srs import review, SRSState

@pytest.mark.parametrize('today', ['2026-11-07', 1, datetime(2026, 11, 7)])
def test_invalid_review_dates_raise_clear_validation_error(today):
    with pytest.raises(ValueError, match='today must be a date'):
        review(SRSState(2.5, 1, 2), 4, today=today)

def test_explicit_date_remains_supported():
    assert review(SRSState(2.5, 1, 0), 4, date(2026, 11, 7)).due_date == date(2026, 11, 8)
