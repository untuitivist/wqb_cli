"""
功能概述
`wqb_core.data.search_fields_limited` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `search_fields_limited(...)`

适用场景
- 作为库模块被导入使用。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 具体参数、返回值和示例以函数签名与方法 docstring 为准。
"""

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "wqb_core.data"

from collections.abc import Iterable

from requests import Response

from ..filter_range import FilterRange
from ..foundation.defines import (
    EQUITY,
    DataCategory,
    Delay,
    FieldType,
    FieldsOrder,
    InstrumentType,
    Region,
    Universe,
)
from ..foundation.urls import URL_DATAFIELDS


class SearchFieldsLimitedMixin:
    def search_fields_limited(
        self,
        region: Region,
        delay: Delay,
        universe: Universe,
        *args,
        instrument_type: InstrumentType = EQUITY,
        dataset_id: str | None = None,
        search: str | None = None,
        category: DataCategory | None = None,
        theme: bool | None = None,
        coverage: FilterRange | None = None,
        type: FieldType | None = None,
        alpha_count: FilterRange | None = None,
        user_count: FilterRange | None = None,
        order: FieldsOrder | None = None,
        limit: int = 50,
        offset: int = 0,
        others: Iterable[str] | None = None,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        搜索 fields，并限制返回规模。
        
        该方法通过 `WQBSession.search_fields_limited(...)` 暴露。
        """
        limit = min(max(limit, 1), 50)
        offset = min(max(offset, 0), 10000 - limit)
        params = [f"region={region}", f"delay={delay}", f"universe={universe}"]
        params.append(f"instrumentType={instrument_type}")
        if dataset_id is not None:
            params.append(f"dataset.id={dataset_id}")
        if search is not None:
            params.append(f"search={search}")
        if category is not None:
            params.append(f"category={category}")
        if theme is not None:
            params.append(f"theme={'true' if theme else 'false'}")
        if coverage is not None:
            params.append(coverage.to_params('coverage'))
        if type is not None:
            params.append(f"type={type}")
        if alpha_count is not None:
            params.append(alpha_count.to_params('alphaCount'))
        if user_count is not None:
            params.append(user_count.to_params('userCount'))
        if order is not None:
            params.append(f"order={order}")
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")
        if others is not None:
            params.extend(others)
        url = URL_DATAFIELDS + '?' + '&'.join(params)
        resp = self.get(url, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join((f"{self}.search_fields_limited(...) [", f"    {url}", f"]: {log}"))
            )
        return resp

if __name__ == "__main__":
    import argparse
    import asyncio
    import inspect
    import json

    from wqb_core import WQBSession
    from requests import Response

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

    parser = argparse.ArgumentParser(description=inspect.getdoc(SearchFieldsLimitedMixin.search_fields_limited) or "")
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

    target = getattr(session, "search_fields_limited")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2, default=str))
