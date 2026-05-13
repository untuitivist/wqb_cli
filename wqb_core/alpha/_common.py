"""
功能概述
`wqb_core.alpha._common` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- 以本模块中定义的公开类、函数和常量为准。

适用场景
- 作为库模块被导入使用。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 具体参数、返回值和示例以函数签名与方法 docstring 为准。
"""

import time
from collections.abc import Callable
from typing import Any

from requests import Response


class WaitForJsonMixin:
    def _wait_for_json(
        self,
        getter: Callable[..., Response],
        alpha_id: str,
        *,
        max_wait_sec: int = 120,
        retry_interval: float = 1.0,
        log: bool = True,
        break_condition: Callable[[Response], bool] = lambda r: r.status_code == 200 and r.text.strip(),
    ) -> dict[str, Any] | None:
        start_time = time.time()
        while time.time() - start_time <= max_wait_sec:
            try:
                resp = getter(alpha_id, log=None, timeout=10)
                if break_condition(resp):
                    return resp.json()
            except Exception as exc:
                if log:
                    self.logger.warning(f"[JSON parse failed] Alpha {alpha_id}: {exc}")
            if log:
                self.logger.info(f"[Waiting] Alpha {alpha_id} result not ready yet.")
            time.sleep(retry_interval)
        if log:
            self.logger.warning(f"[Timeout] Alpha {alpha_id} result was not ready in time.")
        return None
