"""
功能概述
`wqb_core.alpha.patch_properties` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `patch_properties(...)`

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

from collections.abc import Iterable

from requests import Response

from ..foundation.defines import AlphaCategory, Color, Null
from ..foundation.urls import URL_ALPHAS_ALPHAID


class PatchPropertiesMixin:
    def patch_properties(
        self,
        alpha_id: str,
        *args,
        favorite: bool | None = None,
        hidden: bool | None = None,
        name: str | Null | None = None,
        category: AlphaCategory | Null | None = None,
        tags: str | Iterable[str] | Null | None = None,
        color: Color | Null | None = None,
        regular_description: str | Null | None = None,
        selection_description: str | Null | None = None,
        combo_description: str | Null | None = None,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        """
        局部更新 Alpha 属性。
        
        该方法通过 `WQBSession.patch_properties(...)` 暴露。
        """
        url = URL_ALPHAS_ALPHAID.format(alpha_id)
        properties = {}
        if favorite is not None:
            properties['favorite'] = favorite
        if hidden is not None:
            properties['hidden'] = hidden
        if name is not None:
            properties['name'] = None if isinstance(name, Null) else name
        if category is not None:
            properties['category'] = None if isinstance(category, Null) else category
        if tags is not None:
            properties['tags'] = (
                [] if isinstance(tags, Null) else [tags] if isinstance(tags, str) else list(tags)
            )
        if color is not None:
            properties['color'] = None if isinstance(color, Null) else color
        if regular_description is not None:
            properties['regular'] = {'description': None if isinstance(regular_description, Null) else regular_description}
        if selection_description is not None:
            properties['selection'] = {'description': None if isinstance(selection_description, Null) else selection_description}
        if combo_description is not None:
            properties['combo'] = {'description': None if isinstance(combo_description, Null) else combo_description}
        resp = self.patch(url, json=properties, *args, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (f"{self}.patch_properties(...) [", f"    {url}", f"    {properties}", f"]: {log}")
                )
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

    parser = argparse.ArgumentParser(description=inspect.getdoc(PatchPropertiesMixin.patch_properties) or "")
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

    target = getattr(session, "patch_properties")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2, default=str))
