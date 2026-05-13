"""
功能概述
`wqb_core.alpha.filter_alphas_limited` 模块。
这个文件提供 `filter_alphas_limited(...)`，用于按条件过滤当前账号下的 alpha，并限制单次返回规模。

主推荐入口
- `WQBSession.filter_alphas_limited(...)`

适用场景
- 按研究目标塔查看已有 alpha，避免重复方向。
- 按状态、区域、延迟、Universe、Sharpe、Fitness 等条件筛选 alpha。
- 在命令行中快速做“小范围、有上限”的 alpha 池检查。

参数说明
- `status`
  - Alpha 生命周期状态过滤。
  - 当前常用可选值为：
    - `ACTIVE`
    - `UNSUBMITTED`
    - `DECOMMISSIONED`
  - 不要误写成 `SUBMITTED`。
- `region / delay / universe / instrument_type`
  - 用于按目标塔范围缩小筛选范围。
- `limit / offset`
  - 分页控制；`limit` 最大为 `100`。

返回形式
- 返回 `requests.Response`
- `response.json()` 通常包含：
  - `count`
  - `next`
  - `previous`
  - `results`

使用示例
```python
from wqb_core import WQBSession

s = WQBSession()
resp = s.filter_alphas_limited(status="ACTIVE", region="USA", delay=1, limit=20)
print(resp.json())
```

注意事项
- 该方法只返回当前账号的 alpha。
- 如果需要自动翻页或更完整遍历，可使用 `filter_alphas(...)`。
- 平台状态枚举可能调整；若未来接口变化，应以平台实际返回为准。

相关方法
- `filter_alphas(...)`
- `get_alpha_details(...)`
- `get_submission_check(...)`
"""

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "wqb_core.alpha"

from collections.abc import Iterable

from requests import Response

from ..filter_range import FilterRange
from ..foundation.defines import (
    AlphasOrder,
    AlphaCategory,
    AlphaType,
    Color,
    Delay,
    InstrumentType,
    Language,
    NanHandling,
    Neutralization,
    Pasteurization,
    Region,
    Status,
    UnitHandling,
    Universe,
)
from ..foundation.urls import URL_USERS_SELF_ALPHAS


class FilterAlphasLimitedMixin:
    def filter_alphas_limited(
        self,
        *args,
        name: str | None = None,
        competition: bool | None = None,
        type: AlphaType | None = None,
        language: Language | None = None,
        date_created: FilterRange | None = None,
        favorite: bool | None = None,
        date_submitted: FilterRange | None = None,
        start_date: FilterRange | None = None,
        status: Status | None = None,
        category: AlphaCategory | None = None,
        color: Color | None = None,
        tag: str | None = None,
        hidden: bool | None = None,
        region: Region | None = None,
        instrument_type: InstrumentType | None = None,
        universe: Universe | None = None,
        delay: Delay | None = None,
        decay: FilterRange | None = None,
        neutralization: Neutralization | None = None,
        truncation: FilterRange | None = None,
        unit_handling: UnitHandling | None = None,
        nan_handling: NanHandling | None = None,
        pasteurization: Pasteurization | None = None,
        sharpe: FilterRange | None = None,
        returns: FilterRange | None = None,
        pnl: FilterRange | None = None,
        turnover: FilterRange | None = None,
        drawdown: FilterRange | None = None,
        margin: FilterRange | None = None,
        fitness: FilterRange | None = None,
        book_size: FilterRange | None = None,
        long_count: FilterRange | None = None,
        short_count: FilterRange | None = None,
        sharpe60: FilterRange | None = None,
        sharpe125: FilterRange | None = None,
        sharpe250: FilterRange | None = None,
        sharpe500: FilterRange | None = None,
        os_is_sharpe_ratio: FilterRange | None = None,
        pre_close_sharpe: FilterRange | None = None,
        pre_close_sharpe_ratio: FilterRange | None = None,
        self_correlation: FilterRange | None = None,
        prod_correlation: FilterRange | None = None,
        order: AlphasOrder | None = None,
        limit: int = 100,
        offset: int = 0,
        others: Iterable[str] | None = None,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        过滤 Alpha 列表，并限制返回规模。

        参数说明
        - `status`
          - Alpha 生命周期状态过滤。
          - 当前常用可选值为：
            - `ACTIVE`
            - `UNSUBMITTED`
            - `DECOMMISSIONED`
          - 不要误写成 `SUBMITTED`。

        返回形式
        - 返回 `requests.Response`
        """
        limit = min(max(limit, 1), 100)
        offset = min(max(offset, 0), 10000 - limit)
        params = []
        if name is not None:
            params.append(f"name{name if name[0] in '~=' else '~' + name}")
        if competition is not None:
            params.append(f"competition={'true' if competition else 'false'}")
        if type is not None:
            params.append(f"type={type}")
        if language is not None:
            params.append(f"settings.language={language}")
        if date_created is not None:
            params.append(date_created.to_params('dateCreated'))
        if favorite is not None:
            params.append(f"favorite={'true' if favorite else 'false'}")
        if date_submitted is not None:
            params.append(date_submitted.to_params('dateSubmitted'))
        if start_date is not None:
            params.append(start_date.to_params('os.startDate'))
        if status is not None:
            params.append(f"status={status}")
        if category is not None:
            params.append(f"category={category}")
        if color is not None:
            params.append(f"color={color}")
        if tag is not None:
            params.append(f"tag={tag}")
        if hidden is not None:
            params.append(f"hidden={'true' if hidden else 'false'}")
        if region is not None:
            params.append(f"settings.region={region}")
        if instrument_type is not None:
            params.append(f"settings.instrumentType={instrument_type}")
        if universe is not None:
            params.append(f"settings.universe={universe}")
        if delay is not None:
            params.append(f"settings.delay={delay}")
        if decay is not None:
            params.append(decay.to_params('settings.decay'))
        if neutralization is not None:
            params.append(f"settings.neutralization={neutralization}")
        if truncation is not None:
            params.append(truncation.to_params('settings.truncation'))
        if unit_handling is not None:
            params.append(f"settings.unitHandling={unit_handling}")
        if nan_handling is not None:
            params.append(f"settings.nanHandling={nan_handling}")
        if pasteurization is not None:
            params.append(f"settings.pasteurization={pasteurization}")
        if sharpe is not None:
            params.append(sharpe.to_params('is.sharpe'))
        if returns is not None:
            params.append(returns.to_params('is.returns'))
        if pnl is not None:
            params.append(pnl.to_params('is.pnl'))
        if turnover is not None:
            params.append(turnover.to_params('is.turnover'))
        if drawdown is not None:
            params.append(drawdown.to_params('is.drawdown'))
        if margin is not None:
            params.append(margin.to_params('is.margin'))
        if fitness is not None:
            params.append(fitness.to_params('is.fitness'))
        if book_size is not None:
            params.append(book_size.to_params('is.bookSize'))
        if long_count is not None:
            params.append(long_count.to_params('is.longCount'))
        if short_count is not None:
            params.append(short_count.to_params('is.shortCount'))
        if sharpe60 is not None:
            params.append(sharpe60.to_params('os.sharpe60'))
        if sharpe125 is not None:
            params.append(sharpe125.to_params('os.sharpe125'))
        if sharpe250 is not None:
            params.append(sharpe250.to_params('os.sharpe250'))
        if sharpe500 is not None:
            params.append(sharpe500.to_params('os.sharpe500'))
        if os_is_sharpe_ratio is not None:
            params.append(os_is_sharpe_ratio.to_params('os.osISSharpeRatio'))
        if pre_close_sharpe is not None:
            params.append(pre_close_sharpe.to_params('os.preCloseSharpe'))
        if pre_close_sharpe_ratio is not None:
            params.append(pre_close_sharpe_ratio.to_params('os.preCloseSharpeRatio'))
        if self_correlation is not None:
            params.append(self_correlation.to_params('is.selfCorrelation'))
        if prod_correlation is not None:
            params.append(prod_correlation.to_params('is.prodCorrelation'))
        if order is not None:
            params.append(f"order={order}")
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")
        if others is not None:
            params.extend(others)
        url = URL_USERS_SELF_ALPHAS + '?' + '&'.join(params)
        url = url.replace('+', '%2B')
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join((f"{self}.filter_alphas_limited(...) [", f"    {url}", f"]: {log}"))
            )
        return resp


if __name__ == "__main__":
    import argparse
    import asyncio
    import inspect
    import json

    from requests import Response
    from wqb_core import WQBSession

    def _cli_parse_value(text: str):
        lowered = text.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none"}:
            return None
        if text.startswith("@json:"):
            return json.loads(text[6:])
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        return text

    def _cli_collect_unknown(tokens: list[str]) -> dict[str, object]:
        data: dict[str, object] = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if not token.startswith("--"):
                raise SystemExit(f"Unsupported positional argument: {token!r}")
            if "=" in token:
                key_text, value_text = token.split("=", 1)
                key = key_text[2:].replace("-", "_")
                value = _cli_parse_value(value_text)
                if key in data:
                    current = data[key]
                    if isinstance(current, list):
                        current.append(value)
                    else:
                        data[key] = [current, value]
                else:
                    data[key] = value
                i += 1
                continue
            key = token[2:].replace("-", "_")
            if i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
                value = True
                i += 1
            else:
                value = _cli_parse_value(tokens[i + 1])
                i += 2
            if key in data:
                current = data[key]
                if isinstance(current, list):
                    current.append(value)
                else:
                    data[key] = [current, value]
            else:
                data[key] = value
        return data

    def _cli_serialize(value):
        if isinstance(value, Response):
            payload = {
                "status_code": value.status_code,
                "reason": value.reason,
                "url": value.url,
                "headers": dict(value.headers),
            }
            try:
                payload["json"] = value.json()
            except ValueError:
                payload["text"] = value.text
            return payload
        if isinstance(value, dict):
            return {str(k): _cli_serialize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_cli_serialize(v) for v in value]
        if inspect.isgenerator(value):
            return [_cli_serialize(v) for v in list(value)]
        return value

    parser = argparse.ArgumentParser(
        description=inspect.getdoc(FilterAlphasLimitedMixin.filter_alphas_limited) or ""
    )
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--prefer-dotenv")
    parser.add_argument("--dotenv-path")
    args, unknown = parser.parse_known_args()

    session_kwargs = {}
    if args.prefer_dotenv is not None:
        session_kwargs["prefer_dotenv"] = _cli_parse_value(args.prefer_dotenv)
    if args.dotenv_path is not None:
        session_kwargs["dotenv_path"] = args.dotenv_path
    if args.username is not None or args.password is not None:
        if args.username is None or args.password is None:
            raise SystemExit("--username and --password must be provided together")
        session_kwargs["wqb_auth"] = (args.username, args.password)

    session = WQBSession(**session_kwargs)

    target = getattr(session, "filter_alphas_limited")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2, default=str))
