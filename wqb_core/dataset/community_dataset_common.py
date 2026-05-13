"""
功能概述
`wqb_core.dataset.community_dataset_common` 模块。

这个文件提供社区本地数据库的内部支撑能力，包括：
- 默认路径约定
- SQLite 表结构初始化
- forum/docs 数据扁平化
- FTS 索引重建
- 最终 SQLite 落库

主推荐入口
- `dataset_root(...)`
- `default_sqlite_path(...)`
- `write_sqlite(...)`

适用场景
- 为 `export_community_storage` 导入插件导出文件后准备数据库结构
- 把恢复出的 `WQPCommunityState` 写入本地 SQLite
- 为 `search_community_storage` 提供稳定的底层数据表

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 这是内部支撑模块，业务层通常通过更高层的 dataset 能力访问它。
"""

from __future__ import annotations

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "wqb_core.dataset"

import json
import re
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_COMMUNITY_DB = 'forum/community.sqlite3'
_POST_URL_ID_RE = re.compile(r'/community/posts/(?P<post_id>\d+)-')


def dataset_root() -> Path:
    """
    返回社区数据集根目录。
    """
    return Path(__file__).resolve().parent


def default_sqlite_path() -> Path:
    """
    返回默认社区 SQLite 路径。
    """
    return dataset_root() / DEFAULT_COMMUNITY_DB


def ensure_parent(path: Path) -> None:
    """
    确保目标路径的父目录存在。
    """
    path.parent.mkdir(parents=True, exist_ok=True)


def community_json_path(sqlite_path: Path) -> Path:
    """
    返回社区 JSON 快照路径。
    """
    return sqlite_path.with_suffix('.json')


def init_sqlite_schema(conn: sqlite3.Connection) -> None:
    """
    初始化社区 SQLite 表结构。
    """
    conn.executescript(
        '''
        PRAGMA journal_mode=DELETE;
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS forum_communities (
            community_id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            posts INTEGER,
            followers INTEGER,
            raw_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS forum_topics (
            community_id TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            title TEXT,
            url TEXT,
            comment_num INTEGER,
            post_content TEXT,
            last_crawled_at TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (community_id, topic_id)
        );
        CREATE TABLE IF NOT EXISTS forum_comments (
            community_id TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            comment_id TEXT NOT NULL,
            author TEXT,
            comment_time TEXT,
            vote_num INTEGER,
            comment_content TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (community_id, topic_id, comment_id)
        );
        CREATE TABLE IF NOT EXISTS docs_categories (
            category_id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            last_crawled_at TEXT,
            raw_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS docs_sections (
            category_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            title TEXT,
            url TEXT,
            PRIMARY KEY (category_id, section_id)
        );
        CREATE TABLE IF NOT EXISTS docs_articles (
            category_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            article_id TEXT NOT NULL,
            title TEXT,
            url TEXT,
            author TEXT,
            datetime TEXT,
            article_content TEXT,
            last_crawled_at TEXT,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (category_id, section_id, article_id)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS forum_topics_fts USING fts5(
            community_id,
            topic_id,
            title,
            post_content,
            content=''
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS forum_comments_fts USING fts5(
            community_id,
            topic_id,
            comment_id,
            author,
            comment_content,
            content=''
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_articles_fts USING fts5(
            category_id,
            section_id,
            article_id,
            title,
            author,
            article_content,
            content=''
        );
        '''
    )


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """
    重建社区数据库的全文索引表。
    """
    conn.execute('DELETE FROM forum_topics_fts')
    conn.execute('DELETE FROM forum_comments_fts')
    conn.execute('DELETE FROM docs_articles_fts')
    conn.execute(
        '''
        INSERT INTO forum_topics_fts(rowid, community_id, topic_id, title, post_content)
        SELECT rowid, community_id, topic_id, COALESCE(title, ''), COALESCE(post_content, '')
        FROM forum_topics
        '''
    )
    conn.execute(
        '''
        INSERT INTO forum_comments_fts(rowid, community_id, topic_id, comment_id, author, comment_content)
        SELECT rowid, community_id, topic_id, comment_id, COALESCE(author, ''), COALESCE(comment_content, '')
        FROM forum_comments
        '''
    )
    conn.execute(
        '''
        INSERT INTO docs_articles_fts(rowid, category_id, section_id, article_id, title, author, article_content)
        SELECT rowid, category_id, section_id, article_id, COALESCE(title, ''), COALESCE(author, ''), COALESCE(article_content, '')
        FROM docs_articles
        '''
    )


def flatten_forum_topics(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    将 forum 原始结构展开为 communities、topics、comments 记录。
    """
    communities: list[dict[str, Any]] = []
    topics: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    for community_id, community in (payload.get('byCommunity') or {}).items():
        community = community or {}
        reported_posts = int(community.get('posts') or 0)
        communities.append(
            {
                'community_id': str(community_id),
                'title': community.get('title'),
                'url': community.get('url'),
                'posts': reported_posts,
                'followers': int(community.get('followers') or 0),
                'raw_json': json.dumps(community, ensure_ascii=False),
            }
        )
        topic_map = (community.get('topics') or {}) or {}
        raw_ids: set[str] = set()
        url_ids: set[str] = set()
        for topic_id, topic in topic_map.items():
            topic = topic or {}
            raw_ids.add(str(topic_id))
            topic_url = topic.get('url')
            if isinstance(topic_url, str):
                match = _POST_URL_ID_RE.search(topic_url)
                if match:
                    url_ids.add(match.group('post_id'))
                else:
                    url_ids.add(str(topic.get('id') or topic_id))
            else:
                url_ids.add(str(topic.get('id') or topic_id))

        use_url_canonical = True
        if reported_posts > 0:
            raw_gap = abs(len(raw_ids) - reported_posts)
            url_gap = abs(len(url_ids) - reported_posts)
            use_url_canonical = url_gap <= raw_gap

        for topic_id, topic in topic_map.items():
            topic = topic or {}
            topic_url = topic.get('url')
            actual_topic_id = str(topic_id)
            if use_url_canonical and isinstance(topic_url, str):
                match = _POST_URL_ID_RE.search(topic_url)
                if match:
                    actual_topic_id = match.group('post_id')
                else:
                    actual_topic_id = str(topic.get('id') or topic_id)
            elif not use_url_canonical:
                actual_topic_id = str(topic_id)
            topics.append(
                {
                    'community_id': str(community_id),
                    'topic_id': actual_topic_id,
                    'title': topic.get('title'),
                    'url': topic_url,
                    'comment_num': int(topic.get('commentNum') or 0),
                    'post_content': topic.get('postContent'),
                    'last_crawled_at': topic.get('lastCrawledAt'),
                    'raw_json': json.dumps(topic, ensure_ascii=False),
                }
            )
            for comment_id, comment in ((topic.get('comments') or {}) or {}).items():
                comment = comment or {}
                comments.append(
                    {
                        'community_id': str(community_id),
                        'topic_id': actual_topic_id,
                        'comment_id': str(comment_id),
                        'author': comment.get('author'),
                        'comment_time': comment.get('commentTimeDatetime'),
                        'vote_num': int(comment.get('voteNum') or 0),
                        'comment_content': comment.get('commentContent'),
                        'raw_json': json.dumps(comment, ensure_ascii=False),
                    }
                )
    return communities, topics, comments


def flatten_docs(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    将 docs 原始结构展开为 categories、sections、articles 记录。
    """
    categories: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    articles: list[dict[str, Any]] = []
    by_category = payload.get('byCategory') or {}
    for category_id, category in by_category.items():
        category = category or {}
        categories.append(
            {
                'category_id': str(category_id),
                'title': category.get('title'),
                'url': category.get('url'),
                'last_crawled_at': category.get('lastCrawledAt') or payload.get('byCategoryTime'),
                'raw_json': json.dumps(category, ensure_ascii=False),
            }
        )
        section_map = (category.get('sections') or {}) or {}
        for section_id, section in section_map.items():
            section = section or {}
            sections.append(
                {
                    'category_id': str(category_id),
                    'section_id': str(section_id),
                    'title': section.get('title'),
                    'url': section.get('url'),
                }
            )
            for article_id, article in ((section.get('articles') or {}) or {}).items():
                article = article or {}
                articles.append(
                    {
                        'category_id': str(category_id),
                        'section_id': str(section_id),
                        'article_id': str(article_id),
                        'title': article.get('title'),
                        'url': article.get('url'),
                        'author': article.get('author'),
                        'datetime': article.get('datetime'),
                        'article_content': article.get('articleContent'),
                        'last_crawled_at': article.get('lastCrawledAt'),
                        'raw_json': json.dumps(article, ensure_ascii=False),
                    }
                )
    return categories, sections, articles


def write_sqlite(payload: dict[str, Any], sqlite_path: Path) -> dict[str, int]:
    """
    将恢复后的社区 payload 写入 SQLite。
    """
    ensure_parent(sqlite_path)
    temp_file = tempfile.NamedTemporaryFile(
        prefix='wqb_forum_build_',
        suffix='.sqlite3',
        delete=False,
    )
    temp_path = Path(temp_file.name)
    temp_file.close()
    conn = sqlite3.connect(temp_path)
    try:
        init_sqlite_schema(conn)
        communities, topics, comments = flatten_forum_topics(payload)
        categories, sections, articles = flatten_docs(payload)
        conn.executemany(
            '''
            INSERT OR REPLACE INTO forum_communities (
                community_id, title, url, posts, followers, raw_json
            ) VALUES (
                :community_id, :title, :url, :posts, :followers, :raw_json
            )
            ''',
            communities,
        )
        conn.executemany(
            '''
            INSERT OR REPLACE INTO forum_topics (
                community_id, topic_id, title, url, comment_num, post_content, last_crawled_at, raw_json
            ) VALUES (
                :community_id, :topic_id, :title, :url, :comment_num, :post_content, :last_crawled_at, :raw_json
            )
            ''',
            topics,
        )
        conn.executemany(
            '''
            INSERT OR REPLACE INTO forum_comments (
                community_id, topic_id, comment_id, author, comment_time, vote_num, comment_content, raw_json
            ) VALUES (
                :community_id, :topic_id, :comment_id, :author, :comment_time, :vote_num, :comment_content, :raw_json
            )
            ''',
            comments,
        )
        conn.executemany(
            '''
            INSERT OR REPLACE INTO docs_categories (
                category_id, title, url, last_crawled_at, raw_json
            ) VALUES (
                :category_id, :title, :url, :last_crawled_at, :raw_json
            )
            ''',
            categories,
        )
        conn.executemany(
            '''
            INSERT OR REPLACE INTO docs_sections (
                category_id, section_id, title, url
            ) VALUES (
                :category_id, :section_id, :title, :url
            )
            ''',
            sections,
        )
        conn.executemany(
            '''
            INSERT OR REPLACE INTO docs_articles (
                category_id, section_id, article_id, title, url, author, datetime, article_content, last_crawled_at, raw_json
            ) VALUES (
                :category_id, :section_id, :article_id, :title, :url, :author, :datetime, :article_content, :last_crawled_at, :raw_json
            )
            ''',
            articles,
        )
        rebuild_fts(conn)
        conn.execute(
            'INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)',
            ('community_state_json', json.dumps(payload, ensure_ascii=False)),
        )
        conn.execute(
            'INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)',
            ('exported_at', json.dumps({'value': datetime.now().isoformat()})),
        )
        conn.commit()
        conn.close()
        sqlite_path.write_bytes(temp_path.read_bytes())
        return {
            'forum_communities': len(communities),
            'forum_topics': len(topics),
            'forum_comments': len(comments),
            'docs_categories': len(categories),
            'docs_sections': len(sections),
            'docs_articles': len(articles),
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass
        for suffix in ('-shm', '-wal', '-journal'):
            try:
                Path(f'{temp_path}{suffix}').unlink(missing_ok=True)
            except Exception:
                pass
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def row_dicts(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    """
    将 sqlite cursor 结果转换为字典列表。
    """
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row, strict=False)) for row in cursor.fetchall()]


if __name__ == "__main__":
    import argparse

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

    parser = argparse.ArgumentParser(description="Run helper function from this module")
    parser.add_argument("--function", default="dataset_root")
    args, unknown = parser.parse_known_args()

    functions = {
        "dataset_root": dataset_root,
        "default_sqlite_path": default_sqlite_path,
        "ensure_parent": ensure_parent,
        "edge_user_data_dir": edge_user_data_dir,
        "extension_storage_dir": extension_storage_dir,
        "community_json_path": community_json_path,
        "init_sqlite_schema": init_sqlite_schema,
        "rebuild_fts": rebuild_fts,
        "flatten_forum_topics": flatten_forum_topics,
        "flatten_docs": flatten_docs,
        "write_sqlite": write_sqlite,
        "row_dicts": row_dicts,
    }
    try:
        target = functions[args.function]
    except KeyError as exc:
        raise SystemExit(
            f"Unknown function: {args.function!r}. Available: {', '.join(sorted(functions))}"
        ) from exc
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
