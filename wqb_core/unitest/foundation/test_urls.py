import unitest

from wqb_core.foundation import urls


class TestUrls(unitest.TestCase):
    def test_core_urls_exist(self):
        self.assertTrue(urls.URL_AUTHENTICATION.startswith('https://'))
        self.assertIn('/alphas', urls.URL_ALPHAS)


if __name__ == '__main__':
    unitest.main()
