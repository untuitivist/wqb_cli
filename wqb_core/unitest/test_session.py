import unitest

from wqb_core.session import WQBSession


class TestSession(unitest.TestCase):
    def test_session_has_core_methods(self):
        target = WQBSession(prefer_dotenv=False, wqb_auth=('x', 'y'))
        for name in (
            'get_user_profile',
            'get_events',
            'get_pyramid_alphas',
            'export_community_storage',
            'search_community_storage',
            'filter_alphas',
            'run_selection',
        ):
            with self.subTest(name=name):
                self.assertTrue(hasattr(target, name))


if __name__ == '__main__':
    unitest.main()
