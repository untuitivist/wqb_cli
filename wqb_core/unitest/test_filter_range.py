import unitest

from wqb_core.filter_range import FilterRange


class TestFilterRange(unitest.TestCase):
    def test_parse_from_string(self):
        target = FilterRange.parse('[1, 5)')
        self.assertEqual(target.lo, 1)
        self.assertEqual(target.hi, 5)
        self.assertTrue(target.lo_eq)
        self.assertFalse(target.hi_eq)

    def test_to_params(self):
        target = FilterRange(1, 5, True, False)
        self.assertEqual(target.to_params('value'), 'value>=1&value<5')


if __name__ == '__main__':
    unitest.main()
