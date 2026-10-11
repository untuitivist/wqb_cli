from __future__ import annotations

import json


CATEGORY_SQL = """CASE
 WHEN json_type(e.metadata_json, '$.category') = 'object'
 THEN json_extract(e.metadata_json, '$.category.id')
 WHEN json_type(e.metadata_json, '$.category') = 'text'
      AND json_valid(json_extract(e.metadata_json, '$.category'))
 THEN json_extract(json_extract(e.metadata_json, '$.category'), '$.id')
 ELSE json_extract(e.metadata_json, '$.category') END"""


def dispatch_filter(conn):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='library_dispatch_policy'"
    ).fetchone()
    if not exists:
        return ""
    return "AND NOT EXISTS (SELECT 1 FROM library_dispatch_policy p WHERE p.experiment_id=e.id AND p.state!='enabled')"


def select_tower(conn, run_id, now, resend_cutoff):
    row = conn.execute('SELECT metadata_json FROM runs WHERE id=?', (run_id,)).fetchone()
    metadata = json.loads(row['metadata_json']) if row else {}
    policy = metadata.get('tower_balance', {})
    if not policy.get('enabled'):
        return None, None
    counts = policy.setdefault('dispatch_counts', {})
    groups = conn.execute(f"""
        SELECT c.simulation_type,
               json_extract(c.settings_json, '$.region') AS region,
               json_extract(c.settings_json, '$.delay') AS delay,
               {CATEGORY_SQL} AS category,
               MIN(CASE e.state WHEN 'RETRY_WAIT' THEN 0
                    WHEN 'QUEUED' THEN 1 ELSE 2 END) AS dispatch_class
        FROM simulation_queue q JOIN experiments e ON e.id=q.experiment_id
        JOIN candidates c ON c.id=e.candidate_id
        WHERE q.run_id=? AND e.state IN ('QUEUED','RETRY_WAIT','POLLING')
          {dispatch_filter(conn)}
          AND e.not_before<=?
          AND (e.state<>'POLLING' OR (? IS NOT NULL AND q.last_attempt_at<=?))
          AND json_extract(c.settings_json, '$.delay')=1
          AND json_extract(c.settings_json, '$.region') NOT IN ('CHN','CN')
        GROUP BY c.simulation_type, region, delay, category
        ORDER BY RANDOM()
    """, (run_id, now, resend_cutoff, resend_cutoff)).fetchall()
    eligible = []
    for group in groups:
        category = group['category']
        if not isinstance(category, str) or not category or category.upper() == 'UNKNOWN':
            continue
        if category.startswith('{'):
            continue
        eligible.append(group)
    selected = min(eligible, key=lambda group: (
        group['dispatch_class'], counts.get(tower_key(group), 0)
    ), default=None)
    return metadata, selected


def tower_key(group):
    return f"{group['region']}/D{group['delay']}/{group['category']}"


def record_dispatch(conn, run_id, metadata, group, size):
    counts = metadata['tower_balance']['dispatch_counts']
    key = tower_key(group)
    counts[key] = counts.get(key, 0) + size
    conn.execute('UPDATE runs SET metadata_json=? WHERE id=?',
                 (json.dumps(metadata, ensure_ascii=False), run_id))
