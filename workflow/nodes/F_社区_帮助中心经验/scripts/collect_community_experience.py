from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[4]

COMMUNITY_BONUS = {
    "Research Papers for Consultants": 40,
    "顾问专属中文论坛": 35,
    "BRAIN TIPS": 25,
    "Getting started with Research": 20,
    "Global Consultant Community for Staying Ahead": 18,
    "Research Papers for Users": 12,
}

TITLE_ANCHORS = (
    "analyst",
    "estimate",
    "forecast",
    "target price",
    "recommendation",
    "revision",
)


def has_title_anchor(title: str | None) -> bool:
    text = (title or "").lower()
    return any(token in text for token in TITLE_ANCHORS)


def add_hit(store: dict, key: str, payload: dict, query: str, *, title_hit: bool) -> None:
    if key not in store:
        store[key] = {**payload, "query_hits": [query], "title_hit_count": int(title_hit)}
        return
    if query not in store[key]["query_hits"]:
        store[key]["query_hits"].append(query)
    if title_hit:
        store[key]["title_hit_count"] = int(store[key].get("title_hit_count", 0)) + 1


def score_topic(row: dict) -> tuple:
    community_bonus = COMMUNITY_BONUS.get(row.get("community_title") or "", 0)
    title_text = (row.get("title") or "").lower()
    anchor_bonus = sum(1 for token in TITLE_ANCHORS if token in title_text)
    return (
        -(len(row["query_hits"]) * 10 + row.get("title_hit_count", 0) * 8 + community_bonus + anchor_bonus * 4 + min(int(row.get("comment_num") or 0), 80)),
        row["title"],
    )


def score_doc(row: dict) -> tuple:
    title_text = (row.get("title") or "").lower()
    anchor_bonus = sum(1 for token in TITLE_ANCHORS if token in title_text)
    return (
        -(len(row["query_hits"]) * 10 + row.get("title_hit_count", 0) * 8 + anchor_bonus * 4),
        row["title"],
    )


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: collect_community_experience.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    _run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = sys.argv[4]
    category = sys.argv[5].upper()

    q_path = node_dir / f"queries__{region}_D{delay}_{category}.json"
    queries = json.loads(q_path.read_text(encoding="utf-8"))["queries"]

    db_path = ROOT_DIR / "wqb_core" / "dataset" / "forum" / "community.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    topics: dict[str, dict] = {}
    docs: dict[str, dict] = {}

    try:
        for query in queries:
            like = f"%{query}%"

            cur = conn.execute(
                """
                SELECT
                    t.community_id,
                    fc.title AS community_title,
                    t.topic_id,
                    t.title,
                    t.url,
                    t.comment_num
                FROM forum_topics t
                LEFT JOIN forum_communities fc ON fc.community_id = t.community_id
                WHERE COALESCE(t.title, '') LIKE ?
                   OR COALESCE(t.post_content, '') LIKE ?
                LIMIT 15
                """,
                (like, like),
            )
            for row in cur.fetchall():
                title_hit = query.lower() in (row["title"] or "").lower()
                key = f"{row['community_id']}::{row['topic_id']}"
                add_hit(
                    topics,
                    key,
                    {
                        "community_id": row["community_id"],
                        "community_title": row["community_title"],
                        "topic_id": row["topic_id"],
                        "title": row["title"],
                        "url": row["url"],
                        "comment_num": row["comment_num"],
                    },
                    query,
                    title_hit=title_hit,
                )

            cur = conn.execute(
                """
                SELECT
                    a.category_id,
                    a.section_id,
                    a.article_id,
                    a.title,
                    a.url,
                    a.author,
                    a.datetime
                FROM docs_articles a
                WHERE COALESCE(a.title, '') LIKE ?
                   OR COALESCE(a.article_content, '') LIKE ?
                LIMIT 15
                """,
                (like, like),
            )
            for row in cur.fetchall():
                title_hit = query.lower() in (row["title"] or "").lower()
                key = f"{row['category_id']}::{row['section_id']}::{row['article_id']}"
                add_hit(
                    docs,
                    key,
                    {
                        "category_id": row["category_id"],
                        "section_id": row["section_id"],
                        "article_id": row["article_id"],
                        "title": row["title"],
                        "url": row["url"],
                        "author": row["author"],
                        "datetime": row["datetime"],
                    },
                    query,
                    title_hit=title_hit,
                )
    finally:
        conn.close()

    topic_rows = list(topics.values())
    doc_rows = list(docs.values())

    if category.upper() == "ANALYST":
        topic_rows = [
            row for row in topic_rows
            if row.get("title_hit_count", 0) > 0 or has_title_anchor(row.get("title"))
        ]
        doc_rows = [
            row for row in doc_rows
            if row.get("title_hit_count", 0) > 0 or has_title_anchor(row.get("title"))
        ]

    topic_rows = sorted(topic_rows, key=score_topic)
    doc_rows = sorted(doc_rows, key=score_doc)

    out = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "queries": queries,
        "forum_topics": topic_rows[:50],
        "docs_articles": doc_rows[:50],
    }
    out_path = node_dir / f"community_experience__{region}_D{delay}_{category}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
