from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: write_summary.py NODE_DIR REGION DELAY CATEGORY")

    node_dir = Path(sys.argv[1]).resolve()
    region = sys.argv[2]
    delay = sys.argv[3]
    category = sys.argv[4].upper()

    queries_path = node_dir / f"queries__{region}_D{delay}_{category}.json"
    experience_path = node_dir / f"community_experience__{region}_D{delay}_{category}.json"

    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    exp = json.loads(experience_path.read_text(encoding="utf-8"))

    topic_lines = "\n".join(
        f"- `{row['title']}` ({', '.join(row['query_hits'])})"
        for row in exp["forum_topics"][:10]
    ) or "- No forum topics."

    doc_lines = "\n".join(
        f"- `{row['title']}` ({', '.join(row['query_hits'])})"
        for row in exp["docs_articles"][:10]
    ) or "- No docs articles."

    summary = f"""# Community And Help Center Experience

## Queries
- {", ".join(queries["queries"])}

## Outputs
- queries__{region}_D{delay}_{category}.json
- community_experience__{region}_D{delay}_{category}.json

## Top Forum Topics
{topic_lines}

## Top Docs Articles
{doc_lines}
"""
    out_path = node_dir / "node_summary.md"
    out_path.write_text(summary, encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
