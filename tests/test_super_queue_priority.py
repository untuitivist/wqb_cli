import json
import random
import tempfile
import unittest
from collections import Counter
from contextlib import contextmanager
from unittest.mock import patch

from wqb_cli.sqlitesimu.manifest import parse_manifest
from wqb_cli.tests.test_sqlitesimu import SETTINGS, envelope, initialized_store


POLICY = {"super_queue_priority": {"enabled": True, "mode": "within_group"}}


def super_candidate(name, priority, region="USA"):
    return {"type": "SUPER", "selection": "(own)", "combo": name,
            "settings": dict(SETTINGS, region=region), "priority": priority}


@contextmanager
def sampled_without_commit(store):
    generator = random.Random(42)
    original_connect = store.connect

    @contextmanager
    def connection_with_random():
        with original_connect() as connection:
            connection.create_function("random", 0, lambda: generator.randrange(-(2 ** 63), 2 ** 63))
            try:
                yield connection
            finally:
                connection.rollback()

    with patch.object(store, "connect", connection_with_random):
        yield


class SuperQueuePriorityTests(unittest.TestCase):
    def test_opt_in_orders_super_and_keeps_lower_priorities_for_later(self):
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest({"metadata": POLICY, "candidates": [
                super_candidate("low", -1), super_candidate("high", 100), super_candidate("mid", 10),
            ]}), now=1000)
            for name, priority in [("high", 100), ("mid", 10), ("low", -1)]:
                batch = store.create_next_batch(run.run_id, now=1000)
                self.assertEqual(batch.payload["combo"], name)
                with store.connect() as connection:
                    event = connection.execute(
                        "SELECT payload_json FROM api_events WHERE batch_id=? AND event_type='BATCH_CREATED'",
                        (batch.id,),
                    ).fetchone()
                self.assertEqual(json.loads(event["payload_json"])["queue_priority"],
                                 {"mode": "within_group", "priorities": [priority]})
            self.assertIsNone(store.create_next_batch(run.run_id, now=1000))

    def test_default_disabled_and_unknown_modes_remain_random(self):
        for metadata in ({}, {"super_queue_priority": {"enabled": False, "mode": "within_group"}},
                         {"super_queue_priority": {"enabled": True, "mode": "unknown"}},
                         {"super_queue_priority": None}):
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory() as directory:
                store = initialized_store(directory)
                run = store.enqueue(parse_manifest({"metadata": metadata, "candidates": [
                    super_candidate("high", 1000), super_candidate("low", -1000),
                ]}), now=1000)
                chosen = set()
                with sampled_without_commit(store):
                    for _ in range(40):
                        chosen.add(store.create_next_batch(run.run_id, now=1000).payload["combo"])
                self.assertEqual(chosen, {"high", "low"})

    def test_region_sampling_is_independent_of_super_priority_and_queue_size(self):
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest({"metadata": POLICY, "candidates": [
                *[super_candidate(f"usa_{index}", 1000 - index) for index in range(60)],
                super_candidate("rare", -1000, "IND"),
            ]}), now=1000)
            regions = Counter()
            with sampled_without_commit(store):
                for _ in range(128):
                    batch = store.create_next_batch(run.run_id, now=1000)
                    regions[batch.payload["settings"]["region"]] += 1
                    if batch.payload["settings"]["region"] == "USA":
                        self.assertEqual(batch.payload["combo"], "usa_0")
            self.assertGreater(regions["IND"], 40)
            self.assertLess(regions["IND"], 88)

    def test_regular_and_all_ignore_the_super_opt_in(self):
        for simulation_type, region in [("REGULAR", "USA"), ("REGION_AGNOSTIC", "ALL")]:
            with self.subTest(simulation_type=simulation_type), tempfile.TemporaryDirectory() as directory:
                store = initialized_store(directory)
                run = store.enqueue(parse_manifest({"metadata": POLICY, "candidates": [
                    {"type": simulation_type, "regular": f"alpha_{index}",
                     "settings": dict(SETTINGS, region=region,
                                      universe="LARGE" if region == "ALL" else SETTINGS["universe"]),
                     "priority": index}
                    for index in range(12)
                ]}), now=1000)
                expressions = set()
                with sampled_without_commit(store):
                    for _ in range(40):
                        batch = store.create_next_batch(run.run_id, now=1000)
                        payloads = batch.payload if isinstance(batch.payload, list) else [batch.payload]
                        expressions.update(payload["regular"] for payload in payloads)
                self.assertEqual(len(expressions), 12)

    def test_due_retry_precedes_high_priority_new_work(self):
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest({"metadata": POLICY, "candidates": [
                super_candidate("retry", -1000), super_candidate("new", 1000),
            ]}), now=1000)
            with store.connect() as connection:
                connection.execute("UPDATE experiments SET not_before=1010 WHERE priority=1000")
            original = store.create_next_batch(run.run_id, now=1000)
            store.retry_completed_batch(original.id, error="failed", response=envelope(200),
                                        not_before=1010, now=1001)
            self.assertEqual(store.create_next_batch(run.run_id, now=1010).payload["combo"], "retry")

    def test_hidden_retired_accepted_and_unknown_work_stay_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            run = store.enqueue(parse_manifest({"metadata": POLICY, "candidates": [
                super_candidate(name, priority) for name, priority in [
                    ("eligible", 1), ("hidden", 100), ("retired", 100),
                    ("accepted", 100), ("unknown", 100),
                ]
            ]}), now=1000)
            with store.connect() as connection:
                connection.execute("CREATE TABLE library_dispatch_policy (experiment_id TEXT PRIMARY KEY, state TEXT)")
                connection.execute("INSERT INTO library_dispatch_policy SELECT e.id, json_extract(c.payload_json,'$.combo') "
                                   "FROM experiments e JOIN candidates c ON c.id=e.candidate_id "
                                   "WHERE json_extract(c.payload_json,'$.combo') IN ('hidden','retired')")
                for name, state in [("accepted", "POLLING"), ("unknown", "SIMULATE_UNKNOWN")]:
                    connection.execute("UPDATE experiments SET state=? WHERE candidate_id IN "
                                       "(SELECT id FROM candidates WHERE json_extract(payload_json,'$.combo')=?)",
                                       (state, name))
            self.assertEqual(store.create_next_batch(run.run_id, now=1000).payload["combo"], "eligible")
            self.assertIsNone(store.create_next_batch(run.run_id, now=2000))

    def test_priority_respects_an_existing_tower_balance_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            store = initialized_store(directory)
            candidates = []
            for category in ("model", "pv"):
                for name, priority in [("low", 1), ("high", 100)]:
                    candidates.append(dict(super_candidate(category + name, priority), metadata={"category": category}))
            run = store.enqueue(parse_manifest({"metadata": dict(POLICY, tower_balance={"enabled": True}),
                                                "candidates": candidates}), now=1000)
            chosen = [store.create_next_batch(run.run_id, now=1000).payload["combo"] for _ in range(2)]
            self.assertEqual(set(chosen), {"modelhigh", "pvhigh"})


if __name__ == "__main__":
    unittest.main()
