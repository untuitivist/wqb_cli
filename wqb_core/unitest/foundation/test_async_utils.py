import asyncio
import unitest

from wqb_core.foundation.async_utils import api_retry, concurrent_await


class TestAsyncUtils(unitest.TestCase):
    def test_api_retry_returns_value(self):
        class Resp:
            headers = {}

        resp = Resp()
        self.assertIs(api_retry(lambda: resp), resp)

    def test_concurrent_await(self):
        async def main():
            async def one(x):
                return x + 1
            return await concurrent_await([one(1), one(2)])
        result = asyncio.run(main())
        self.assertEqual(result, [2, 3])


if __name__ == '__main__':
    unitest.main()
