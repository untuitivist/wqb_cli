"""
功能概述
`wqb_core.simulation.simulate` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `simulate(...)`

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
    __package__ = "wqb_core.simulation"

from collections.abc import Callable, Coroutine, Iterable
from typing import Any

from requests import Response

from ..foundation.defines import GET, LOCATION, Alpha, MultiAlpha
from ..foundation.urls import URL_SIMULATIONS


class SimulateMixin:
    async def simulate(
        self,
        target: Alpha | MultiAlpha,
        *args,
        max_tries: int | Iterable[Any] = range(600),
        on_nolocation: Callable[[dict[str, Any]], None] | None = None,
        log: str | None = '',
        retry_log: str | None = None,
        **kwargs,
    ) -> Coroutine[None, None, Response | None]:
        """
        提交 simulation，并等待最终结果。
        
        该方法通过 `WQBSession.simulate(...)` 暴露。
        
        这是一个异步方法；若直接在脚本中运行，入口会自动处理事件循环。
        """
        resp = self.post(
            URL_SIMULATIONS,
            json=target,
            expected=self.expected_location,
            max_tries=60,
            delay_unexpected=5.0,
        )
        try:
            url = resp.headers[LOCATION]
        except KeyError as exc:
            if resp.status_code != 429:
                self.logger.warning(f"Simulation failed: {resp.status_code} {resp.reason} {resp.text}")
            else:
                self.logger.warning(
                    '\n'.join(
                        (
                            f"{self}.simulate(...) [",
                            f"    {repr(exc)}",
                            f"    {target}",
                            "]:",
                            f"{resp}:",
                            f"    status_code: {resp.status_code}",
                            f"    reason: {resp.reason}",
                            f"    url: {resp.url}",
                            f"    elapsed: {resp.elapsed}",
                            f"    headers: {resp.headers}",
                            f"    text: {resp.text}",
                        )
                    )
                )
            if on_nolocation is not None:
                on_nolocation(locals())
            return None
        resp = await self.retry(GET, url, *args, max_tries=max_tries, log=retry_log, **kwargs)
        if log is not None:
            self.logger.info('\n'.join((f"{self}.simulate(...) [", f"    {url}", f"]: {log}")))
        return resp

if __name__ == "__main__":
    import argparse
    import asyncio
    import inspect
    import json
    import sys
    from pathlib import Path

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
        if text.startswith("@file:"):
            return json.loads(Path(text[6:]).read_text(encoding="utf-8-sig"))
        if text.startswith("@jsonfile:"):
            return json.loads(Path(text[10:]).read_text(encoding="utf-8-sig"))
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

    parser = argparse.ArgumentParser(description=inspect.getdoc(SimulateMixin.simulate) or "")
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

    target = getattr(session, "simulate")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2, default=str))
