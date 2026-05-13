"""
功能概述
`wqb_core.alpha.set_alpha_properties` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `set_alpha_properties(...)`

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
    __package__ = "wqb_core.alpha"

from ..foundation.defines import Null


class SetAlphaPropertiesMixin:
    def set_alpha_properties(
        self,
        alpha_id: str,
        *args,
        name: str | None = None,
        color: str | None = None,
        category: str | None = None,
        regular_desc: str | None = None,
        selection_desc: str | None = None,
        combo_desc: str | None = None,
        osmosis_points: int | None = None,
        tags: list[str] | None = None,
        log: str | None = '',
        **kwargs,
    ):
        """
        设置 Alpha 属性。
        
        该方法通过 `WQBSession.set_alpha_properties(...)` 暴露。
        """
        if osmosis_points is not None and not (1 <= osmosis_points <= 100000):
            raise ValueError(f'osmosis_points must be between 1 and 100000, got {osmosis_points}')
        resp = self.patch_properties(
            alpha_id,
            *args,
            name=name if name is not None else None,
            color=color if color is not None else None,
            category=category if category is not None else None,
            tags=tags if tags is not None else None,
            regular_description=regular_desc if regular_desc is not None else None,
            selection_description=selection_desc if selection_desc is not None else None,
            combo_description=combo_desc if combo_desc is not None else None,
            log=log,
            **kwargs,
        )
        if osmosis_points is not None:
            payload = resp.json()
            payload['osmosisPoints'] = osmosis_points
            return payload
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

    parser = argparse.ArgumentParser(description=inspect.getdoc(SetAlphaPropertiesMixin.set_alpha_properties) or "")
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

    target = getattr(session, "set_alpha_properties")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2, default=str))
