import unitest
from datetime import datetime, timedelta

from wqb_core.datetime_range import DatetimeRange


class TestDatetimeRange(unitest.TestCase):
    def test_basic_iteration_and_length(self):
        target = DatetimeRange(
            datetime(2026, 1, 1, 0, 0, 0),
            datetime(2026, 1, 1, 3, 0, 0),
            timedelta(hours=1),
        )
        self.assertEqual(len(target), 3)
        self.assertEqual(list(target), [
            datetime(2026, 1, 1, 0, 0, 0),
            datetime(2026, 1, 1, 1, 0, 0),
            datetime(2026, 1, 1, 2, 0, 0),
        ])

    def test_contains_and_index(self):
        target = DatetimeRange(
            datetime(2026, 1, 1, 0, 0, 0),
            datetime(2026, 1, 1, 3, 0, 0),
            timedelta(hours=1),
        )
        point = datetime(2026, 1, 1, 1, 0, 0)
        self.assertIn(point, target)
        self.assertEqual(target.index(point), 1)


if __name__ == '__main__':
    unitest.main()
