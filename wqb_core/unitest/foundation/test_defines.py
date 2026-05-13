import unitest

from wqb_core.foundation.defines import GET, POST, Null


class TestDefines(unitest.TestCase):
    def test_http_constants(self):
        self.assertEqual(GET, 'GET')
        self.assertEqual(POST, 'POST')

    def test_null_type(self):
        self.assertIsInstance(Null(), Null)


if __name__ == '__main__':
    unitest.main()
