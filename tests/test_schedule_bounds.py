import unittest
from datetime import date, timedelta

from app.srs import SRSState, review


class ScheduleBoundsTests(unittest.TestCase):
    def test_mature_card_caps_interval_and_due_date_together(self):
        today = date(2026, 10, 22)
        result = review(SRSState(2.5, 2_000_000, 30), 4, today=today)
        self.assertEqual(result.due_date, date.max)
        self.assertEqual(result.interval_days, (date.max - today).days)
        self.assertEqual(result.repetitions, 31)

    def test_repeated_easy_reviews_remain_schedulable(self):
        today = date(2026, 10, 22)
        state = SRSState(2.5, 0, 0)
        for _ in range(100):
            result = review(state, 5, today=today)
            self.assertEqual(result.due_date, today + timedelta(days=result.interval_days))
            state = SRSState(result.ease_factor, result.interval_days, result.repetitions)
        self.assertEqual(result.due_date, date.max)

    def test_final_supported_date_does_not_overflow(self):
        result = review(SRSState(2.5, 0, 0), 0, today=date.max)
        self.assertEqual(result.due_date, date.max)
        self.assertEqual(result.interval_days, 0)

    def test_ordinary_intervals_are_preserved(self):
        today = date(2026, 10, 22)
        result = review(SRSState(2.5, 6, 2), 4, today=today)
        self.assertEqual(result.interval_days, 15)
        self.assertEqual(result.due_date, today + timedelta(days=15))
