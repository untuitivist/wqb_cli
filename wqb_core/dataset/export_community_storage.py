"""
功能概述
`wqb_core.dataset.export_community_storage` 模块。

这个模块负责把 WebDataScope 插件导出的社区数据文件导入为本地 SQLite。
支持两种插件导出格式：
- `WQPCommunityState_*.json`
- `WQPCommunityState_*.wqcs`（msgpack + zlib 压缩）

主推荐入口
- `export_community_storage(...)`

适用场景
- 插件已经通过弹窗导出社区数据，希望稳定导入本地知识库。
- 不再直接解析浏览器插件的 LevelDB 缓存。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 当前实现不再保留 LevelDB 回退路径。
- 推荐优先使用插件导出的 JSON；`.wqcs` 作为压缩导出格式同样支持。
"""

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "wqb_core.dataset"

import json
import zlib
from pathlib import Path
from typing import Any

import msgpack

from .community_dataset_common import (
    DEFAULT_COMMUNITY_DB,
    community_json_path,
    default_sqlite_path,
    write_sqlite,
)


class ExportCommunityStorageMixin:
    """
    导入插件导出的社区数据文件并生成本地 SQLite。

    参数说明
    - `source_path`:
      - 插件导出的 `.json` 或 `.wqcs` 文件路径。
      - 省略时，会优先在 `wqb_core/dataset/forum` 中自动寻找最新的
        `WQPCommunityState_*` 导出文件，然后再回退到常见下载目录和外部样例目录。
    - `sqlite_path`:
      - 目标 SQLite 路径。
      - 省略时使用 `wqb_core/dataset/forum/community.sqlite3`。
    - `export_json`:
      - 是否把导入后的 payload 再落一份规范化 JSON 到 SQLite 同目录。
    - `log`:
      - 透传给 logger 的附加日志文本。

    返回形式
    - 返回 `dict`，包含：
      - `source_file`
      - `source_format`
      - `sqlite_path`
      - `json_path`
      - `payload_stats`
      - `counts`
    """

    @staticmethod
    def _downloads_dir() -> Path:
        return Path.home() / 'Downloads'

    @staticmethod
    def _forum_dir() -> Path:
        return default_sqlite_path().parent

    @classmethod
    def _candidate_export_files(cls) -> list[Path]:
        patterns = [
            'WQPCommunityState_*.json',
            'WQPCommunityState_*.wqcs',
        ]
        roots = [
            cls._forum_dir(),
            cls._downloads_dir(),
            Path(r'U:\Project\MainCode\3.Work\WQB\WebDataScope-0.9.3'),
        ]
        candidates: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            for pattern in patterns:
                candidates.extend(root.glob(pattern))
        candidates = [p for p in candidates if p.is_file()]
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates

    @classmethod
    def _resolve_source_file(cls, source_path: str | Path | None) -> Path:
        if source_path:
            path = Path(source_path)
            if not path.exists():
                raise FileNotFoundError(f'Community export file not found: {path}')
            if not path.is_file():
                raise FileNotFoundError(f'Community export path is not a file: {path}')
            return path

        candidates = cls._candidate_export_files()
        if not candidates:
            raise FileNotFoundError(
                'No plugin community export file found. '
                'Please export WQPCommunityState from the WebDataScope popup first.'
            )
        return candidates[0]

    @staticmethod
    def _load_json_payload(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(payload, dict):
            raise ValueError(f'Community export JSON must decode to dict: {path}')
        return payload

    @staticmethod
    def _load_wqcs_payload(path: Path) -> dict[str, Any]:
        raw = path.read_bytes()
        inflated = zlib.decompress(raw)
        payload = msgpack.loads(inflated, raw=False)
        if not isinstance(payload, dict):
            raise ValueError(f'Community export WQCS must decode to dict: {path}')
        return payload

    @classmethod
    def _load_payload(cls, source_file: Path) -> tuple[dict[str, Any], str]:
        suffix = source_file.suffix.lower()
        if suffix == '.json':
            return cls._load_json_payload(source_file), 'json'
        if suffix == '.wqcs':
            return cls._load_wqcs_payload(source_file), 'wqcs'
        raise ValueError(f'Unsupported community export format: {source_file}')

    @staticmethod
    def _payload_stats(payload: dict[str, Any]) -> dict[str, int]:
        by_community = payload.get('byCommunity') or {}
        by_category = payload.get('byCategory') or {}
        topic_count = 0
        comment_count = 0
        for community in by_community.values():
            topics = (community or {}).get('topics') or {}
            topic_count += len(topics)
            for topic in topics.values():
                comment_count += len(((topic or {}).get('comments') or {}))
        article_count = 0
        section_count = 0
        for category in by_category.values():
            sections = (category or {}).get('sections') or {}
            section_count += len(sections)
            for section in sections.values():
                article_count += len(((section or {}).get('articles') or {}))
        return {
            'communities': len(by_community),
            'topics': topic_count,
            'comments': comment_count,
            'categories': len(by_category),
            'sections': section_count,
            'articles': article_count,
        }

    def export_community_storage(
        self,
        *,
        source_path: str | Path | None = None,
        sqlite_path: str | Path | None = None,
        export_json: bool = False,
        log: str | None = '',
    ) -> dict:
        """
        从插件导出的社区数据文件导入社区数据库。

        该方法通过 `WQBSession.export_community_storage(...)` 暴露。
        """
        source_file = self._resolve_source_file(source_path)
        payload, source_format = self._load_payload(source_file)

        sqlite_target = Path(sqlite_path) if sqlite_path else default_sqlite_path()
        counts = write_sqlite(payload, sqlite_target)

        raw_json_path = None
        if export_json:
            raw_json_path = community_json_path(sqlite_target)
            raw_json_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )

        result = {
            'source_file': str(source_file),
            'source_format': source_format,
            'sqlite_path': str(sqlite_target),
            'json_path': str(raw_json_path) if raw_json_path else None,
            'payload_stats': self._payload_stats(payload),
            'counts': counts,
        }
        if log is not None:
            self.logger.info(f"{self}.export_community_storage(...): {log}")
        return result


if __name__ == "__main__":
    import argparse
    import asyncio
    import inspect

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
        return value

    parser = argparse.ArgumentParser(
        description="导入 WebDataScope 插件导出的社区数据文件，生成本地 SQLite。"
    )
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--prefer-dotenv", dest="prefer_dotenv")
    parser.add_argument("--dotenv-path", dest="dotenv_path")
    parser.add_argument("--help-method", action="store_true")
    args, unknown = parser.parse_known_args()

    if args.help_method:
        method = ExportCommunityStorageMixin.export_community_storage
        print(inspect.signature(method))
        print(inspect.getdoc(method) or "")
        raise SystemExit(0)

    kwargs = _cli_collect_unknown(unknown)
    session = WQBSession(
        username=args.username,
        password=args.password,
        prefer_dotenv=_cli_parse_value(args.prefer_dotenv) if args.prefer_dotenv is not None else True,
        dotenv_path=args.dotenv_path,
    )
    result = session.export_community_storage(**kwargs)
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2))
