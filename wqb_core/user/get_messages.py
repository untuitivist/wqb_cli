"""
功能概述
`wqb_core.user.get_messages` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `get_messages(...)`

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
    __package__ = "wqb_core.user"

import base64
import os
import pathlib
import re

from requests import Response

from ..foundation.urls import URL_USERS_SELF_MESSAGES


class GetMessagesMixin:
    def get_messages(
        self,
        *args,
        limit: int | None = None,
        offset: int = 0,
        log: str | None = '',
        **kwargs,
    ) -> dict:
        """
        获取消息列表。
        
        该方法通过 `WQBSession.get_messages(...)` 暴露。
        """
        url = URL_USERS_SELF_MESSAGES
        params = {}
        if limit is not None:
            params['limit'] = limit
        if offset > 0:
            params['offset'] = offset
        resp = self.get(url, *args, params=params, **kwargs)
        resp.raise_for_status()
        data = resp.json()
        image_handling = os.environ.get('BRAIN_MESSAGE_IMAGE_MODE', 'placeholder').lower()
        save_dir = pathlib.Path('message_images')

        def process_description(desc: str, message_id: str) -> tuple[str, list[str]]:
            if not desc or image_handling == 'keep':
                return desc, []
            attachments = []
            img_tag_pattern = re.compile(r'<img[^>]+src=\"(data:image/[^\"]+)\"[^>]*>', re.IGNORECASE)
            matches = list(img_tag_pattern.finditer(desc))
            if not matches:
                heuristic_pattern = re.compile(r'([A-Za-z0-9+/]{500,}={0,2})\"\s*</img>')
                if image_handling != 'keep' and heuristic_pattern.search(desc):
                    return heuristic_pattern.sub('[Embedded image removed - large base64 sequence truncated]</img>', desc), []
                return desc, []
            if image_handling == 'placeholder':
                save_dir.mkdir(parents=True, exist_ok=True)
            new_desc = desc
            for idx, match in enumerate(matches, start=1):
                data_uri = match.group(1)
                if ',' not in data_uri:
                    continue
                header, b64_data = data_uri.split(',', 1)
                mime_part = header.split(';')[0]
                ext = mime_part.split('/')[1] if '/' in mime_part else 'img'
                if image_handling == 'ignore':
                    replacement = f'[Image removed: {ext}]'
                else:
                    file_path = save_dir / f'{message_id}_{idx}.{ext}'
                    try:
                        if len(b64_data) > 7_000_000:
                            raise ValueError('Image too large to decode safely')
                        with open(file_path, 'wb') as f:
                            f.write(base64.b64decode(b64_data))
                        attachments.append(str(file_path))
                        replacement = f'[Image extracted -> {file_path}]'
                    except Exception:
                        replacement = '[Image extraction failed - content omitted]'
                new_desc = new_desc.replace(match.group(0), replacement, 1)
            return new_desc, attachments

        results = data.get('results', [])
        for msg in results:
            desc = msg.get('description')
            processed_desc, attachments = process_description(desc, msg.get('id', 'msg'))
            if attachments or desc != processed_desc:
                msg['description'] = processed_desc
                if attachments:
                    msg['extracted_images'] = attachments
                else:
                    msg['sanitized'] = True
        data['results'] = results
        data['image_handling'] = image_handling
        if log is not None:
            self.logger.info('\n'.join((f"{self}.get_messages(...) [", f"    {url}", f"]: {log}")))
        return data

if __name__ == "__main__":
    import argparse
    import asyncio
    import inspect
    import json
    import sys

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

    parser = argparse.ArgumentParser(description=inspect.getdoc(GetMessagesMixin.get_messages) or "")
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

    target = getattr(session, "get_messages")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2, default=str))
