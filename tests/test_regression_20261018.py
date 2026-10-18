import unittest
from app.srs import review, SRSState

class QualityTests(unittest.TestCase):
    def test_invalid_grades_raise_value_error(self):
        for quality in [True, False, 3.5, 4.0, '4', None, -1, 6]:
            with self.subTest(quality=quality), self.assertRaises(ValueError):
                review(SRSState(2.5, 1, 0), quality)

    def test_all_integer_grades_are_supported(self):
        for quality in range(6):
            self.assertGreaterEqual(review(SRSState(2.5, 1, 0), quality).interval_days, 1)
