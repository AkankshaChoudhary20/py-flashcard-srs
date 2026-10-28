import pytest
from app.srs import SRSState, review


@pytest.mark.parametrize('ease', [0, -1, float('nan'), float('inf'), True])
def test_invalid_ease_factor_is_rejected(ease):
    with pytest.raises(ValueError, match='ease_factor'):
        review(SRSState(ease, 6, 2), 4)


@pytest.mark.parametrize('interval,repetitions', [(-1, 2), (1.5, 2), (True, 2), (6, -1), (6, 2.5), (6, False)])
def test_invalid_counters_are_rejected(interval, repetitions):
    with pytest.raises(ValueError):
        review(SRSState(2.5, interval, repetitions), 4)
