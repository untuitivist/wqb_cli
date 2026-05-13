import unitest

from wqb_core.foundation.credentials import load_dotenv_values, resolve_wqb_auth


class TestCredentials(unitest.TestCase):
    def test_load_dotenv_values_missing_file(self):
        self.assertEqual(load_dotenv_values('definitely_missing.env'), {})

    def test_resolve_wqb_auth_tuple(self):
        auth = resolve_wqb_auth(('u', 'p'), prefer_dotenv=False)
        self.assertEqual(auth.username, 'u')
        self.assertEqual(auth.password, 'p')


if __name__ == '__main__':
    unitest.main()
