import json
import tempfile
import unittest
from collections import Counter

from wqb_cli.sqlitesimu.db import SqliteStore
from wqb_cli.sqlitesimu.manifest import parse_manifest
from wqb_cli.tests.test_sqlitesimu import SETTINGS, initialized_store


class TowerBalanceTests(unittest.TestCase):
    def test_balance_is_by_expression_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            store = initialized_store(folder)
            candidates = []
            for category, count in [('model', 300), ('pv', 40), ('sentiment', 40)]:
                for number in range(count):
                    candidates.append({'expression': f'close + {number} + {len(candidates)}',
                        'settings': SETTINGS, 'metadata': {'category': {'id': category}}})
            candidates.append({'expression': 'close + 9999', 'settings': dict(SETTINGS, region='CHN'),
                               'metadata': {'category': 'pv'}})
            manifest = parse_manifest({'metadata': {'tower_balance': {'enabled': True}}, 'candidates': candidates})
            run = store.enqueue(manifest, now=1000)
            counts = Counter()
            for step in range(9):
                store = SqliteStore(store.path)
                batch = store.create_next_batch(run.run_id, now=1001 + step)
                self.assertIsNotNone(batch)
                with store.connect() as connection:
                    rows = connection.execute('''SELECT e.metadata_json,c.settings_json FROM simulation_items si
                        JOIN experiments e ON e.id=si.experiment_id JOIN candidates c ON c.id=e.candidate_id
                        WHERE si.batch_id=?''', (batch.id,)).fetchall()
                categories = {json.loads(row['metadata_json'])['category']['id'] for row in rows}
                self.assertEqual(len(categories), 1)
                self.assertTrue(all(json.loads(row['settings_json'])['region'] != 'CHN' for row in rows))
                counts[next(iter(categories))] += len(rows)
            self.assertEqual(dict(counts), {'model': 30, 'pv': 30, 'sentiment': 30})

    def test_unknown_category_does_not_get_a_fake_tower(self):
        with tempfile.TemporaryDirectory() as folder:
            store = initialized_store(folder)
            run = store.enqueue(parse_manifest({'metadata': {'tower_balance': {'enabled': True}},
                'candidates': [{'expression': 'close', 'settings': SETTINGS}]}), now=1000)
            self.assertIsNone(store.create_next_batch(run.run_id, now=1001))

    def test_single_all_and_regular_ten_receive_equal_expression_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            store = initialized_store(folder)
            candidates = []
            for number in range(30):
                candidates.append({'expression': f'close + {number}', 'settings': SETTINGS,
                                   'metadata': {'category': 'pv'}})
                candidates.append({'payload': {'type': 'REGION_AGNOSTIC', 'regular': f'close + {number}',
                    'settings': dict(SETTINGS, region='ALL', universe='LARGE')},
                    'metadata': {'category': '{"id":"pv"}'}})
            run = store.enqueue(parse_manifest({'metadata': {'tower_balance': {'enabled': True}},
                                                'candidates': candidates}), now=1000)
            for step in range(11):
                batch = store.create_next_batch(run.run_id, now=1001 + step)
                self.assertIsNotNone(batch)
            with store.connect() as connection:
                metadata = json.loads(connection.execute('SELECT metadata_json FROM runs WHERE id=?',
                                                         (run.run_id,)).fetchone()[0])
            self.assertEqual(sorted(metadata['tower_balance']['dispatch_counts'].values()), [10, 10])


if __name__ == '__main__':
    unittest.main()
