import unitest

from wqb_core import WQBSession


class TestRootInit(unitest.TestCase):
    def test_wqbsession_exposed(self):
        self.assertIs(WQBSession.__name__, 'WQBSession')


if __name__ == '__main__':
    unitest.main()
