"""
功能概述
`wqb_core.foundation.helpers` 模块。

这个文件提供常用基础工具，包括：
- 自动 flush 的 `print`
- 默认风格的 `wqb_logger`
- 将单 Alpha 序列切成 multi-alpha 的 `to_multi_alphas`

主推荐入口
- `print(...)`
- `wqb_logger(...)`
- `to_multi_alphas(...)`

适用场景
- 研究脚本中及时刷新日志输出
- 为 `WQBSession` 或独立脚本构建统一风格 logger
- 手工理解和构造 multi-alpha 分槽结果

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- `to_multi_alphas` 只做简单切片，不负责校验 `language/instrumentType/region/delay` 一致性。
"""

import datetime
import logging
import os
from collections.abc import Generator, Iterable
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from .defines import Alpha, MultiAlpha

__all__ = ['print', 'wqb_logger', 'to_multi_alphas']


_print = print


def print(*args, **kwargs) -> None:
    """
    输出内容，并强制立即 flush。
    """
    kwargs['flush'] = True
    _print(*args, **kwargs)


def wqb_logger(
    *,
    log_dir: str = 'logs',
    name: str | None = None,
    backupCount: int = -1,
) -> logging.Logger:
    """
    创建 `wqb_core` 默认风格的 logger。
    """
    if name is None:
        name = 'wqb' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f'{name}.log')
    logger = logging.getLogger(name=name)
    logger.setLevel(logging.INFO)
    if backupCount == -1:
        handler1 = logging.FileHandler(log_file_path, encoding='utf-8')
    else:
        handler1 = TimedRotatingFileHandler(
            log_file_path,
            when='midnight',
            interval=1,
            backupCount=backupCount,
            encoding='utf-8',
        )
    handler1.setLevel(logging.INFO)
    handler1.setFormatter(
        logging.Formatter(fmt='# %(levelname)s %(asctime)s\n%(message)s\n')
    )
    logger.addHandler(handler1)
    handler2 = logging.StreamHandler()
    handler2.setLevel(logging.WARNING)
    handler2.setFormatter(
        logging.Formatter(fmt='# %(levelname)s %(asctime)s\n%(message)s\n')
    )
    logger.addHandler(handler2)
    return logger


def to_multi_alphas(
    alphas: Iterable[Alpha],
    multiple: int | Iterable[Any],
) -> Generator[MultiAlpha, None, None]:
    """
    按指定槽大小把单个 Alpha 序列切成 multi-alpha。
    """
    alphas = iter(alphas)
    multiple = range(multiple) if isinstance(multiple, int) else tuple(multiple)
    try:
        while True:
            multi_alpha = []
            for _ in multiple:
                multi_alpha.append(next(alphas))
            yield multi_alpha
    except StopIteration:
        if 0 < len(multi_alpha):
            yield multi_alpha
