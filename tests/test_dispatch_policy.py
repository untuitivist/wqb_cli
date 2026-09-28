import json
import tempfile
import unittest

from test_sqlitesimu import SETTINGS, initialized_store
from wqb_cli.sqlitesimu.manifest import parse_manifest


class DispatchPolicyTests(unittest.TestCase):
    def test_disabled_retries_cannot_bypass_dispatch_policy(self):
        for balanced in (False, True):
            with self.subTest(balanced=balanced), tempfile.TemporaryDirectory() as directory:
                store = initialized_store(directory)
                run = store.enqueue(parse_manifest([
                    {'expression': 'rank(close)', 'settings': SETTINGS, 'metadata': {'category': 'PV'}},
                    {'expression': 'rank(volume)', 'settings': SETTINGS, 'metadata': {'category': 'PV'}},
                    {'expression': 'rank(returns)', 'settings': SETTINGS, 'metadata': {'category': 'PV'}},
                ]), now=1000)
                with store.connect() as conn:
                    experiments = conn.execute('SELECT id FROM experiments ORDER BY id').fetchall()
                    conn.execute('CREATE TABLE library_dispatch_policy (experiment_id TEXT PRIMARY KEY, state TEXT, updated_at REAL)')
                    conn.executemany('INSERT INTO library_dispatch_policy VALUES (?,?,1000)', [
                        (experiments[0]['id'], 'hidden'), (experiments[1]['id'], 'retired'),
                        (experiments[2]['id'], 'enabled'),
                    ])
                    conn.execute("UPDATE experiments SET state='RETRY_WAIT', attempts=1")
                    if balanced:
                        conn.execute('UPDATE runs SET metadata_json=?', (json.dumps({'tower_balance': {'enabled': True}}),))
                batch = store.create_next_batch(run.run_id, now=1001)
                self.assertIsNotNone(batch)
                with store.connect() as conn:
                    selected = conn.execute('SELECT experiment_id FROM simulation_items WHERE batch_id=?', (batch.id,)).fetchall()
                    self.assertEqual([row[0] for row in selected], [experiments[2]['id']])
                self.assertIsNone(store.create_next_batch(run.run_id, now=1001))
                with store.connect() as conn:
                    conn.execute("UPDATE library_dispatch_policy SET state='enabled' WHERE experiment_id=?", (experiments[0]['id'],))
                restored = store.create_next_batch(run.run_id, now=1002)
                self.assertIsNotNone(restored)
                with store.connect() as conn:
                    self.assertEqual(conn.execute('SELECT experiment_id FROM simulation_items WHERE batch_id=?', (restored.id,)).fetchone()[0], experiments[0]['id'])
