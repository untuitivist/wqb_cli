from __future__ import annotations

import json
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen


ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_query(query: str, start: int = 0, max_results: int = 5) -> list[dict]:
    params = {
        "search_query": f"all:{query}",
        "start": start,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = ARXIV_API + "?" + urllib.parse.urlencode(params)
    with urlopen(url, timeout=30) as resp:
        payload = resp.read()
    root = ET.fromstring(payload)
    rows: list[dict] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip().replace("\n", " ")
        summary = (entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").strip().replace("\n", " ")
        published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
        entry_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
        authors = [a.findtext("atom:name", default="", namespaces=ATOM_NS) for a in entry.findall("atom:author", ATOM_NS)]
        categories = [c.attrib.get("term", "") for c in entry.findall("atom:category", ATOM_NS)]
        rows.append(
            {
                "title": title,
                "summary": summary,
                "published": published,
                "id": entry_id,
                "authors": authors,
                "categories": categories,
                "query": query,
            }
        )
    return rows


def score_entry(row: dict) -> tuple:
    text = (row.get("title", "") + " " + row.get("summary", "")).lower()
    score = 0
    anchors = [
        "analyst", "forecast", "revision", "target price", "recommendation",
        "earnings", "dispersion", "coverage", "stock return",
    ]
    for token in anchors:
        if token in text:
            score += 1
    return (-score, row.get("published", ""), row.get("title", ""))


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit("Usage: search_arxiv.py RUN_DIR NODE_DIR REGION DELAY CATEGORY")

    _run_dir = Path(sys.argv[1]).resolve()
    node_dir = Path(sys.argv[2]).resolve()
    region = sys.argv[3].upper()
    delay = sys.argv[4]
    category = sys.argv[5].upper()

    q_obj = json.loads((node_dir / f"queries__{region}_D{delay}_{category}.json").read_text(encoding="utf-8"))
    queries = q_obj["queries"]

    results: list[dict] = []
    seen_ids: set[str] = set()
    for query in queries:
        rows = fetch_query(query, 0, 5)
        for row in rows:
            if row["id"] in seen_ids:
                continue
            seen_ids.add(row["id"])
            results.append(row)
        time.sleep(0.8)

    results = sorted(results, key=score_entry)
    out = {
        "region": region,
        "delay": int(delay),
        "category": category,
        "queries": queries,
        "count": len(results),
        "results": results[:25],
    }
    out_path = node_dir / f"arxiv_results__{region}_D{delay}_{category}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
