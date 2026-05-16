"""
功能概述
`wqb_core.user.get_pyramid_alphas` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `get_pyramid_alphas(...)`

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

from datetime import date, datetime

from requests import Response

from ..foundation.urls import (
    URL_ACTIVITIES_PYRAMID_ALPHAS,
    URL_USERS_SELF_ACTIVITIES_PYRAMID_ALPHAS,
    URL_USERS_SELF_PYRAMID_ALPHAS,
)


class GetPyramidAlphasMixin:
    @staticmethod
    def _quarter_date_range(year: int, quarter: int) -> tuple[str, str]:
        if quarter not in (1, 2, 3, 4):
            raise ValueError('quarter must be one of 1, 2, 3, or 4')
        quarter_starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
        quarter_ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
        start_month, start_day = quarter_starts[quarter]
        end_month, end_day = quarter_ends[quarter]
        return (
            date(year, start_month, start_day).isoformat(),
            date(year, end_month, end_day).isoformat(),
        )

    @classmethod
    def _current_quarter_date_range(cls) -> tuple[str, str, int, int]:
        today = datetime.today()
        quarter = ((today.month - 1) // 3) + 1
        start_date, end_date = cls._quarter_date_range(today.year, quarter)
        return start_date, end_date, today.year, quarter

    @staticmethod
    def _build_url(url: str, params: dict[str, str]) -> str:
        if not params:
            return url
        return url + '?' + '&'.join(f'{key}={value}' for key, value in params.items())

    def _get_pyramid_alphas_raw(
        self,
        url: str,
        params: dict[str, str],
        *args,
        log: str | None = '',
        **kwargs,
    ) -> Response:
        resp = self.get(url, *args, params=params, **kwargs)
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}._get_pyramid_alphas_raw(...) [",
                        f"    {self._build_url(url, params)}",
                        f"]: {log}",
                    )
                )
            )
        return resp

    def get_pyramid_alphas(
        self,
        *args,
        start_date: str | None = None,
        end_date: str | None = None,
        scope: str = 'all',
        quarter: int | None = None,
        year: int | None = None,
        log: str | None = '',
        **kwargs,
    ) -> dict:
        """
        获取金字塔 Alpha 提交统计。
        
        该方法通过 `WQBSession.get_pyramid_alphas(...)` 暴露。
        """
        params: dict[str, str] = {}
        resolved_scope = (scope or 'all').lower()
        resolved_start = start_date
        resolved_end = end_date

        if resolved_start or resolved_end:
            resolved_scope = 'custom'
        elif quarter is not None:
            resolved_scope = 'quarter'
            resolved_year = year or datetime.today().year
            resolved_start, resolved_end = self._quarter_date_range(resolved_year, quarter)
            year = resolved_year
        elif resolved_scope == 'quarter':
            resolved_start, resolved_end, resolved_year, resolved_quarter = (
                self._current_quarter_date_range()
            )
            year = resolved_year
            quarter = resolved_quarter
        elif resolved_scope != 'all':
            return {
                'error': "Invalid scope. Use 'all' or 'quarter', or provide start_date/end_date."
            }

        if resolved_start is not None:
            params['startDate'] = resolved_start
        if resolved_end is not None:
            params['endDate'] = resolved_end

        tried_urls = (
            URL_USERS_SELF_ACTIVITIES_PYRAMID_ALPHAS,
            URL_USERS_SELF_PYRAMID_ALPHAS,
            URL_ACTIVITIES_PYRAMID_ALPHAS,
        )
        resp = None
        for url in tried_urls:
            resp = self._get_pyramid_alphas_raw(url, params, *args, log=None, **kwargs)
            if resp.status_code != 404:
                break

        assert resp is not None
        if resp.status_code == 404:
            if log is not None:
                self.logger.info(
                    '\n'.join(
                        (
                            f"{self}.get_pyramid_alphas(...) [",
                            f"    {self._build_url(tried_urls[0], params)}",
                            f"]: {log}",
                        )
                    )
                )
            return {
                'error': 'Pyramid alphas endpoint not found',
                'tried_endpoints': [
                    '/users/self/activities/pyramid-alphas',
                    '/users/self/pyramid/alphas',
                    '/activities/pyramid-alphas',
                ],
            }

        resp.raise_for_status()
        payload = resp.json()
        pyramids = payload.get('pyramids', [])
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.get_pyramid_alphas(...) [",
                        f"    {self._build_url(resp.request.url.split('?')[0], params)}",
                        f"]: {log}",
                    )
                )
            )
        return {
            'scope': resolved_scope,
            'start_date': resolved_start,
            'end_date': resolved_end,
            'quarter': quarter,
            'year': year,
            'count': len(pyramids),
            'data': payload,
        }

if __name__ == "__main__":
    import argparse
    import asyncio
    import inspect
    import json
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

    parser = argparse.ArgumentParser(description=inspect.getdoc(GetPyramidAlphasMixin.get_pyramid_alphas) or "")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--prefer-dotenv")
    parser.add_argument("--dotenv-path")
    parser.add_argument("--output", help="Write serialized JSON result to this path instead of stdout.")
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

    target = getattr(session, "get_pyramid_alphas")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    serialized = _cli_serialize(result)
    text = json.dumps(serialized, ensure_ascii=False, indent=2, default=str)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        print(text)
