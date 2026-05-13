"""
功能概述
`wqb_core.dataset.search_community_storage` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `search_community_storage(...)`

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
    __package__ = "wqb_core.dataset"

import sqlite3
from pathlib import Path

from .community_dataset_common import (
    DEFAULT_COMMUNITY_DB,
    default_sqlite_path,
    dataset_root,
    row_dicts,
)


class SearchCommunityStorageMixin:
    @staticmethod
    def _resolve_sqlite_path(sqlite_path: str | Path | None) -> Path:
        if sqlite_path:
            return Path(sqlite_path)
        return default_sqlite_path()

    @staticmethod
    def _like_pattern(query: str) -> str:
        return f'%{query}%'

    def search_community_storage(
        self,
        query: str,
        *,
        sqlite_path: str | Path | None = None,
        scope: str = 'all',
        limit: int = 20,
        log: str | None = '',
    ) -> dict:
        """
        在本地社区数据库中执行离线搜索。
        
        该方法通过 `WQBSession.search_community_storage(...)` 暴露。
        """
        db_path = self._resolve_sqlite_path(sqlite_path)
        if not db_path.exists():
            raise FileNotFoundError(f'Community sqlite dataset not found: {db_path}')
        limit = max(1, min(int(limit), 200))
        scope = scope.lower().strip()
        conn = sqlite3.connect(db_path)
        try:
            result = {
                'sqlite_path': str(db_path),
                'query': query,
                'scope': scope,
                'forum_topics': [],
                'forum_comments': [],
                'docs_articles': [],
            }
            if scope in ('all', 'forum', 'topics'):
                cur = conn.execute(
                    '''
                    SELECT
                        t.community_id,
                        fc.title AS community_title,
                        t.topic_id,
                        t.title,
                        t.url,
                        t.comment_num,
                        t.last_crawled_at
                    FROM forum_topics t
                    LEFT JOIN forum_communities fc
                      ON fc.community_id = t.community_id
                    WHERE COALESCE(t.title, '') LIKE ?
                       OR COALESCE(t.post_content, '') LIKE ?
                    LIMIT ?
                    ''',
                    (self._like_pattern(query), self._like_pattern(query), limit),
                )
                result['forum_topics'] = row_dicts(cur)
            if scope in ('all', 'forum', 'comments'):
                cur = conn.execute(
                    '''
                    SELECT
                        c.community_id,
                        fc.title AS community_title,
                        c.topic_id,
                        c.comment_id,
                        c.author,
                        c.comment_time,
                        c.vote_num
                    FROM forum_comments c
                    LEFT JOIN forum_communities fc
                      ON fc.community_id = c.community_id
                    WHERE COALESCE(c.author, '') LIKE ?
                       OR COALESCE(c.comment_content, '') LIKE ?
                    LIMIT ?
                    ''',
                    (self._like_pattern(query), self._like_pattern(query), limit),
                )
                result['forum_comments'] = row_dicts(cur)
            if scope in ('all', 'docs', 'articles'):
                cur = conn.execute(
                    '''
                    SELECT a.category_id, a.section_id, a.article_id, a.title, a.url, a.author, a.datetime
                    FROM docs_articles a
                    WHERE COALESCE(a.title, '') LIKE ?
                       OR COALESCE(a.author, '') LIKE ?
                       OR COALESCE(a.article_content, '') LIKE ?
                    LIMIT ?
                    ''',
                    (
                        self._like_pattern(query),
                        self._like_pattern(query),
                        self._like_pattern(query),
                        limit,
                    ),
                )
                result['docs_articles'] = row_dicts(cur)
            if log is not None:
                self.logger.info(f"{self}.search_community_storage(...): {log}")
            return result
        finally:
            conn.close()

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

    parser = argparse.ArgumentParser(description=inspect.getdoc(SearchCommunityStorageMixin.search_community_storage) or "")
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

    target = getattr(session, "search_community_storage")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2, default=str))
