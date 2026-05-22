from __future__ import annotations

import unittest

from wqb_cli.commands.sim import (
    _child_simulation_ids,
    _classify_simulation_create,
    _classify_simulation_result,
)


class SimulationTests(unittest.TestCase):
    def test_classify_create_as_waiting_for_results(self) -> None:
        result = {
            "ok": True,
            "response": {
                "status_code": 201,
                "location": "https://api.worldquantbrain.com/simulations/SIM123",
            },
        }

        classified = _classify_simulation_create(result)

        self.assertTrue(classified["ok"])
        self.assertEqual(classified["reason"], "simulation_created_waiting_for_results")
        self.assertEqual(classified["message"], "201 Created, waiting for results...")

    def test_classify_timeout_as_failure(self) -> None:
        result = {
            "ok": True,
            "response": {
                "wait_timed_out": True,
                "body": {"status": "PENDING"},
            },
        }

        classified = _classify_simulation_result(result)

        self.assertFalse(classified["ok"])
        self.assertEqual(classified["reason"], "simulation_wait_timed_out")

    def test_classify_warning_as_finished(self) -> None:
        result = {
            "ok": True,
            "response": {
                "wait_timed_out": False,
                "body": {"status": "WARNING", "alpha": "abc"},
            },
        }

        classified = _classify_simulation_result(result)

        self.assertTrue(classified["ok"])
        self.assertEqual(classified["reason"], "simulation_finished")

    def test_child_simulation_ids_accept_strings_and_objects(self) -> None:
        result = {
            "response": {
                "body": {
                    "children": [
                        "child-a",
                        {"id": "child-b"},
                        {"bad": "child-c"},
                    ]
                }
            }
        }

        self.assertEqual(_child_simulation_ids(result), ["child-a", "child-b"])


if __name__ == "__main__":
    unittest.main()
