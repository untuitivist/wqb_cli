"""
功能概述
`wqb_core.foundation.async_utils` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `api_retry(...)`

适用场景
- 作为库模块被导入使用。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 具体参数、返回值和示例以函数签名与方法 docstring 为准。
"""

import asyncio
import time
from collections.abc import Awaitable, Coroutine, Iterable
from typing import Any

__all__ = ['concurrent_await', 'api_retry']


async def concurrent_await(
    awaitables: Iterable[Awaitable[Any]],
    *,
    concurrency: int | asyncio.Semaphore | None = None,
    return_exceptions: bool = False,
) -> Coroutine[None, None, list[Any | BaseException]]:
    if concurrency is None:
        return await asyncio.gather(*awaitables)
    if isinstance(concurrency, int):
        concurrency = asyncio.Semaphore(value=concurrency)

    async def semaphore_wrapper(
        awaitable: Awaitable[Any],
    ) -> Coroutine[None, None, Any]:
        async with concurrency:
            result = await awaitable
        return result

    return await asyncio.gather(
        *(semaphore_wrapper(awaitable) for awaitable in awaitables),
        return_exceptions=return_exceptions,
    )


def api_retry(get_fn, *args, max_wait=300, **kwargs) -> Any:
    """
    重复调用异步 API，直到满足停止条件。
    """
    start = time.time()
    while True:
        resp = get_fn(*args, **kwargs)
        if 'retry-after' in resp.headers:
            time.sleep(float(resp.headers['retry-after']))
        else:
            return resp
        if time.time() - start > max_wait:
            return None
