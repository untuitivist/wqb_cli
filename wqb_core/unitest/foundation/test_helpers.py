import unitest

from wqb_core.foundation.helpers import to_multi_alphas


class TestHelpers(unitest.TestCase):
    def test_to_multi_alphas(self):
        target = list(to_multi_alphas([1, 2, 3], 2))
        self.assertEqual(target, [[1, 2], [3]])


if __name__ == '__main__':
    unitest.main()
