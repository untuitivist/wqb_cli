from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from wqb_cli.agent.artifacts import (
    ArtifactError,
    ArtifactWriter,
    NODE_DIRECTORIES,
    redact_argv,
    redact_text,
)
from wqb_cli.agent.policy import AgentPolicy, PolicyViolation
from wqb_cli.agent.runner import (
    REPO_ROOT,
    AgentRunner,
    RunnerError,
    command_fingerprint,
    sanitized_environment,
)
from wqb_cli.agent.store import AgentStore
from wqb_cli.agent.types import Budget, RunConfig, ScopeMode, WorkflowNode


def command_record(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": 11,
        "status": "STARTED",
        "resource_id": None,
        "artifact_id": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class AgentRunnerFirstRedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Mock()
        self.runner = AgentRunner(
            self.store,
            AgentPolicy(Budget()),
            ArtifactWriter(self.root),
        )

    def test_policy_rejection_precedes_artifact_validation_and_execution(self) -> None:
        with patch("wqb_cli.agent.runner.subprocess.run") as run:
            with self.assertRaises(PolicyViolation):
                self.runner.run(
                    "run-1",
                    WorkflowNode.J,
                    ("alpha", "submit", "A1"),
                    "bad.json",
                )

        self.store.reserve_command.assert_not_called()
        run.assert_not_called()

    def test_completed_command_reuses_verified_json_artifact(self) -> None:
        path = self.root / "run-1" / "10_J" / "result.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"ok":true}', encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        artifact = SimpleNamespace(
            id=7,
            run_id="run-1",
            node=WorkflowNode.J,
            name="result.json",
            path=str(path),
            sha256=digest,
            kind="json",
        )
        self.store.reserve_command.return_value = command_record(
            status="COMPLETED", resource_id="SIM1", artifact_id=7
        )
        self.store.get_artifact.return_value = artifact

        with patch("wqb_cli.agent.runner.subprocess.run") as run:
            result = self.runner.run(
                "run-1",
                WorkflowNode.J,
                ("sim", "get", "SIM1"),
                "result.json",
            )

        self.assertEqual(result.payload, {"ok": True})
        self.assertTrue(result.reused)
        self.assertEqual(result.artifact, artifact)
        run.assert_not_called()

    def test_recovery_of_sim_create_inspects_existing_resource(self) -> None:
        self.store.reserve_command.return_value = command_record(
            status="RECOVERY_REQUIRED", resource_id="SIM1"
        )
        self.store.add_or_update_artifact.return_value = SimpleNamespace(id=8)
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"simulation_id":"SIM1","ok":true}\n', stderr=""
        )

        with patch("wqb_cli.agent.runner.subprocess.run", return_value=completed) as run:
            result = self.runner.run(
                "run-1",
                WorkflowNode.J,
                ("sim", "create", "--input", "candidate.json"),
                "result.json",
            )

        executed = run.call_args.args[0]
        self.assertEqual(
            executed[-5:],
            ["sim", "get", "SIM1", "--max-wait-seconds", "900"],
        )
        self.assertNotIn("create", executed)
        self.assertFalse(result.reused)
        self.store.complete_command.assert_called_once_with(11, 0, artifact_id=8)


class ArtifactWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.writer = ArtifactWriter(self.root)

    def test_node_directories_preserve_alphabetic_numbers_while_skipping_e(self) -> None:
        self.assertEqual(NODE_DIRECTORIES[WorkflowNode.A], "01_A")
        self.assertEqual(NODE_DIRECTORIES[WorkflowNode.F], "06_F")
        self.assertEqual(NODE_DIRECTORIES[WorkflowNode.M], "13_M")
        self.assertNotIn("05_E", NODE_DIRECTORIES.values())

    def test_run_id_and_artifact_name_reject_cross_platform_escape_shapes(self) -> None:
        bad_runs = (
            "",
            "   ",
            ".",
            "..",
            "a/b",
            "a\\b",
            "C:",
            "C:\\run",
            "\\\\host\\share",
        )
        for run_id in bad_runs:
            with self.subTest(run_id=run_id), self.assertRaises(ArtifactError):
                self.writer.write_json(run_id, WorkflowNode.A, "x.json", {})

        bad_names = (
            "",
            ".",
            "../x.json",
            "nested/../../x.json",
            "nested/",
            "nested\\",
            "/tmp/x.json",
            "C:\\tmp\\x.json",
            "C:x.json",
            "\\\\host\\share\\x.json",
            "x\x00.json",
        )
        for name in bad_names:
            with self.subTest(name=name), self.assertRaises(ArtifactError):
                self.writer.write_json("run", WorkflowNode.A, name, {})

    def test_safe_nested_name_is_allowed_but_symlink_escape_is_rejected(self) -> None:
        artifact = self.writer.write_json(
            "run", WorkflowNode.A, "nested/result.json", {"ok": True}
        )
        self.assertTrue(Path(artifact.path).is_file())
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir(exist_ok=True)
        self.addCleanup(lambda: outside.rmdir() if outside.exists() else None)
        link = self.root / "run" / "01_A" / "escape"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks are unavailable")
        with self.assertRaises(ArtifactError):
            self.writer.write_json("run", WorkflowNode.A, "escape/x.json", {})

    def test_atomic_failure_removes_unique_temporary_file(self) -> None:
        with patch("wqb_cli.agent.artifacts.os.replace", side_effect=OSError("fail")):
            with self.assertRaises(OSError):
                self.writer.write_json("run", WorkflowNode.A, "result.json", {})
        directory = self.root / "run" / "01_A"
        self.assertEqual(list(directory.glob("*.tmp")), [])
        self.assertEqual(list(directory.glob(".*.tmp")), [])

    @unittest.skipUnless(os.name == "nt", "Windows handle verification")
    def test_windows_temp_handle_is_verified_before_secret_bytes_are_written(self) -> None:
        outside = self.root.parent / f"{self.root.name}-escaped" / "temp.tmp"
        with patch.object(
            self.writer, "_final_path_for_fd", return_value=outside
        ), self.assertRaises(ArtifactError):
            self.writer.write_markdown(
                "run", WorkflowNode.A, "secret.md", "password=never-write-this"
            )
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"never-write-this", path.read_bytes())

    def test_concurrent_writes_use_distinct_temporary_names(self) -> None:
        failures: list[BaseException] = []

        def write(index: int) -> None:
            try:
                self.writer.write_json(
                    "run", WorkflowNode.A, f"nested/{index}.json", {"index": index}
                )
            except BaseException as exc:
                failures.append(exc)

        threads = [threading.Thread(target=write, args=(index,)) for index in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(failures, [])
        self.assertEqual(len(list((self.root / "run" / "01_A" / "nested").glob("*.json"))), 12)

    def test_concurrent_same_name_keeps_registry_hash_consistent_with_file(self) -> None:
        class DelayedStore:
            def __init__(self) -> None:
                self.first_entered = threading.Event()
                self.calls = 0
                self.current: SimpleNamespace | None = None
                self.guard = threading.Lock()

            def add_or_update_artifact(
                inner_self,
                run_id: str,
                node: WorkflowNode,
                name: str,
                path: Path,
                sha256: str,
                kind: str,
            ) -> SimpleNamespace:
                with inner_self.guard:
                    inner_self.calls += 1
                    call_number = inner_self.calls
                if call_number == 1:
                    inner_self.first_entered.set()
                    threading.Event().wait(0.2)
                record = SimpleNamespace(
                    id=call_number,
                    run_id=run_id,
                    node=node,
                    name=name,
                    path=str(path),
                    sha256=sha256,
                    kind=kind,
                )
                inner_self.current = record
                return record

        store = DelayedStore()
        writer = self.writer.with_store(store)
        first = threading.Thread(
            target=writer.write_json,
            args=("run", WorkflowNode.A, "same.json", {"value": "first"}),
        )
        second = threading.Thread(
            target=writer.write_json,
            args=("run", WorkflowNode.A, "same.json", {"value": "second"}),
        )
        first.start()
        self.assertTrue(store.first_entered.wait(1))
        second.start()
        first.join()
        second.join()
        self.assertIsNotNone(store.current)
        self.assertIn(writer.read_json(store.current)["value"], {"first", "second"})

    def test_json_is_canonical_strict_redacted_and_discards_secret_values(self) -> None:
        cyclic: list[object] = []
        cyclic.append(cyclic)
        artifact = self.writer.write_json(
            "run",
            WorkflowNode.A,
            "result.json",
            {
                "z": 1,
                "api_key": cyclic,
                "entry": {"name": "clientSecret", "value": "never-write"},
                "ordinary": "visible",
            },
        )
        rendered = Path(artifact.path).read_text(encoding="utf-8")
        self.assertEqual(
            rendered,
            '{"api_key":"[REDACTED]","entry":{"name":"clientSecret","value":"[REDACTED]"},"ordinary":"visible","z":1}',
        )
        self.assertNotIn("never-write", rendered)
        for value in ([1], {1: "x"}, {"n": float("nan")}, {"x": object()}):
            with self.subTest(value=value), self.assertRaises(ArtifactError):
                self.writer.write_json("run", WorkflowNode.A, "bad.json", value)  # type: ignore[arg-type]

    def test_markdown_and_argv_redaction_remove_values_but_keep_safe_data(self) -> None:
        secrets = (
            "bearer-secret",
            "cookie-secret",
            "api-secret",
            "pass-secret",
            "client-secret-value",
            "access-token-value",
            "private-key-value",
        )
        text = (
            "Authorization: Bearer bearer-secret\nCookie=cookie-secret\n"
            "api_key: api-secret\n--password pass-secret\n"
            "--client-secret client-secret-value\n--access-token=access-token-value\n"
            "--private-key private-key-value\nordinary: visible"
        )
        redacted = redact_text(text)
        for secret in secrets:
            self.assertNotIn(secret, redacted)
        self.assertIn("ordinary: visible", redacted)
        safe = redact_argv(
            (
                "auth",
                "login",
                "--password",
                "pass-secret",
                "--api-key=api-secret",
                "--client-secret",
                "client-secret-value",
                "--access-token=access-token-value",
                "--private-key",
                "private-key-value",
                "visible",
            )
        )
        self.assertEqual(
            safe,
            (
                "auth",
                "login",
                "--password",
                "[REDACTED]",
                "--api-key=[REDACTED]",
                "--client-secret",
                "[REDACTED]",
                "--access-token=[REDACTED]",
                "--private-key",
                "[REDACTED]",
                "visible",
            ),
        )

    def test_registered_hash_detects_tampering_and_forged_in_root_path(self) -> None:
        artifact = self.writer.write_json("run", WorkflowNode.A, "result.json", {"ok": True})
        self.assertEqual(self.writer.read_json(artifact), {"ok": True})
        Path(artifact.path).write_text('{"ok":false}', encoding="utf-8")
        with self.assertRaises(ArtifactError):
            self.writer.read_json(artifact)

        other = self.writer.write_json("other", WorkflowNode.B, "other.json", {"wrong": True})
        forged = SimpleNamespace(
            **{
                **artifact.__dict__,
                "path": other.path,
                "sha256": other.sha256,
            }
        )
        with self.assertRaises(ArtifactError):
            self.writer.read_json(forged)

        missing = self.writer.write_json(
            "run", WorkflowNode.A, "missing.json", {"ok": True}
        )
        Path(missing.path).unlink()
        with self.assertRaises(ArtifactError):
            self.writer.read_json(missing)

        for invalid_hash in (None, "", "0" * 63, "z" * 64):
            with self.subTest(invalid_hash=invalid_hash):
                invalid = SimpleNamespace(**{**other.__dict__, "sha256": invalid_hash})
                with self.assertRaises(ArtifactError):
                    self.writer.read_json(invalid)

    def test_registry_failure_is_controlled_and_does_not_claim_an_artifact(self) -> None:
        store = Mock()
        store.add_or_update_artifact.side_effect = RuntimeError("registry-secret")
        writer = self.writer.with_store(store)
        with self.assertRaises(ArtifactError) as raised:
            writer.write_json("run", WorkflowNode.A, "result.json", {"ok": True})
        self.assertNotIn("registry-secret", str(raised.exception))


class AgentRunnerBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Mock()
        self.store.reserve_command.return_value = command_record()
        self.next_artifact_id = 20

        def register(run_id: str, node: WorkflowNode, name: str, path: Path, sha256: str, kind: str) -> SimpleNamespace:
            self.next_artifact_id += 1
            return SimpleNamespace(
                id=self.next_artifact_id,
                run_id=run_id,
                node=node,
                name=name,
                path=str(path),
                sha256=sha256,
                kind=kind,
            )

        self.store.add_or_update_artifact.side_effect = register
        self.runner = AgentRunner(
            self.store, AgentPolicy(Budget()), ArtifactWriter(self.root), timeout_seconds=7
        )

    def test_subprocess_contract_and_sanitized_environment_are_exact(self) -> None:
        completed = subprocess.CompletedProcess([], 0, '{"ok":true}', "safe stderr")
        with patch.dict(
            os.environ,
            {"PATH": "safe-path", "WQB_PASSWORD": "fake-password", "API_KEY": "fake-api"},
            clear=True,
        ), patch("wqb_cli.agent.runner.subprocess.run", return_value=completed) as run:
            result = self.runner.run(
                "run", WorkflowNode.J, ("sim", "get", "SIM1"), "result.json"
            )

        self.assertEqual(result.payload, {"ok": True})
        args, kwargs = run.call_args
        self.assertEqual(args[0], [os.sys.executable, "-m", "wqb_cli", "sim", "get", "SIM1"])
        self.assertEqual(kwargs["cwd"], REPO_ROOT)
        self.assertIs(kwargs["shell"], False)
        self.assertIs(kwargs["text"], True)
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["stdout"], subprocess.PIPE)
        self.assertEqual(kwargs["stderr"], subprocess.PIPE)
        self.assertEqual(kwargs["timeout"], 7)
        self.assertIs(kwargs["check"], False)
        self.assertEqual(kwargs["env"], {"PATH": "safe-path"})
        self.assertNotIn("fake-password", repr(run.call_args))

        isolated = AgentRunner(
            self.store,
            AgentPolicy(Budget()),
            ArtifactWriter(self.root / "isolated-artifacts"),
            command_cwd=self.root,
        )
        self.store.reserve_command.return_value = command_record(id=99)
        with patch("wqb_cli.agent.runner.subprocess.run", return_value=completed) as run:
            isolated.run(
                "isolated", WorkflowNode.J, ("sim", "get", "SIM1"), "result.json"
            )
        self.assertEqual(run.call_args.kwargs["cwd"], self.root.resolve())

    def test_python_startup_path_environment_is_removed(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PATH": "safe-path",
                "PYTHONPATH": "attacker-path",
                "PYTHONHOME": "attacker-home",
            },
            clear=True,
        ):
            self.assertEqual(sanitized_environment(), {"PATH": "safe-path"})

    def test_valid_policy_but_invalid_artifact_input_fails_before_reservation(self) -> None:
        with patch("wqb_cli.agent.runner.subprocess.run") as run, self.assertRaises(ArtifactError):
            self.runner.run(
                "run", WorkflowNode.J, ("sim", "get", "SIM1"), "../escape.json"
            )
        self.store.reserve_command.assert_not_called()
        run.assert_not_called()

    def test_file_fingerprint_uses_content_not_location(self) -> None:
        first = self.root / "first.json"
        second = self.root / "second.json"
        first.write_bytes(b'{"x":1}')
        second.write_bytes(first.read_bytes())
        one = command_fingerprint(WorkflowNode.J, ("sim", "create", "--input", str(first)))
        two = command_fingerprint(WorkflowNode.J, ("sim", "create", f"--input={second}"))
        self.assertEqual(one, two)
        second.write_bytes(b'{"x":2}')
        self.assertNotEqual(one, command_fingerprint(WorkflowNode.J, ("sim", "create", "--input", str(second))))
        candidate = self.root / "candidate"
        candidate.write_bytes(b"first-content")
        input_one = command_fingerprint(
            WorkflowNode.J,
            ("sim", "create", "--input", "candidate"),
            cwd=self.root,
        )
        resource_one = command_fingerprint(
            WorkflowNode.J, ("sim", "get", "candidate"), cwd=self.root
        )
        candidate.write_bytes(b"second-content")
        self.assertNotEqual(
            input_one,
            command_fingerprint(
                WorkflowNode.J,
                ("sim", "create", "--input", "candidate"),
                cwd=self.root,
            ),
        )
        self.assertEqual(
            resource_one,
            command_fingerprint(
                WorkflowNode.J, ("sim", "get", "candidate"), cwd=self.root
            ),
        )
        output = self.root / "result.json"
        output.write_bytes(b"first-output")
        output_one = command_fingerprint(
            WorkflowNode.J,
            ("sim", "get", "SIM1", "--output", "result.json"),
            cwd=self.root,
        )
        output.write_bytes(b"second-output")
        self.assertEqual(
            output_one,
            command_fingerprint(
                WorkflowNode.J,
                ("sim", "get", "SIM1", "--output", "result.json"),
                cwd=self.root,
            ),
        )
        info = self.root / "info_data.bin"
        info.write_bytes(b"info-one")
        scope_one = command_fingerprint(
            WorkflowNode.F,
            ("scope", "files", "--info", "info_data.bin"),
            cwd=self.root,
        )
        info.write_bytes(b"info-two")
        self.assertNotEqual(
            scope_one,
            command_fingerprint(
                WorkflowNode.F,
                ("scope", "files", "--info", "info_data.bin"),
                cwd=self.root,
            ),
        )
        sqlite = self.root / "community.sqlite3"
        sqlite.write_bytes(b"sqlite-one")
        community_one = command_fingerprint(
            WorkflowNode.G,
            ("community", "search", "factor", "--sqlite=community.sqlite3"),
            cwd=self.root,
        )
        sqlite.write_bytes(b"sqlite-two")
        self.assertNotEqual(
            community_one,
            command_fingerprint(
                WorkflowNode.G,
                ("community", "search", "factor", "--sqlite=community.sqlite3"),
                cwd=self.root,
            ),
        )
        with patch("wqb_cli.agent.runner.Path.cwd", return_value=Path(__file__).parents[1]):
            self.assertIsInstance(
                command_fingerprint(WorkflowNode.G, ("docs", "list")), str
            )

    def test_success_result_is_redacted_and_command_log_accumulates(self) -> None:
        outcomes = [
            subprocess.CompletedProcess([], 0, '{"api_key":"first-secret","ok":true}', ""),
            subprocess.CompletedProcess([], 0, '{"password":"second-secret","ok":true}', ""),
        ]
        self.store.reserve_command.side_effect = [command_record(id=31), command_record(id=32)]
        with patch("wqb_cli.agent.runner.subprocess.run", side_effect=outcomes):
            first = self.runner.run(
                "run", WorkflowNode.J, ("sim", "get", "SIM1"), "first.json"
            )
            second = self.runner.run(
                "run", WorkflowNode.J, ("sim", "get", "SIM2"), "second.json"
            )
        self.assertEqual(first.payload["api_key"], "[REDACTED]")
        self.assertEqual(second.payload["password"], "[REDACTED]")
        log = self.root / "run" / "10_J" / "commands.jsonl"
        lines = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        rendered = repr((first, second, lines))
        self.assertNotIn("first-secret", rendered)
        self.assertNotIn("second-secret", rendered)

    def test_nonzero_timeout_oserror_and_malformed_output_fail_without_retry(self) -> None:
        cases = (
            subprocess.CompletedProcess([], 4, "{}", "password=stderr-secret"),
            subprocess.TimeoutExpired(["safe"], 7),
            OSError("password=oserror-secret"),
            subprocess.CompletedProcess([], 0, "prose {\"ok\":true}", ""),
            subprocess.CompletedProcess([], 0, "{} {}", ""),
            subprocess.CompletedProcess([], 0, "[]", ""),
            subprocess.CompletedProcess([], 0, '{"x":NaN}', ""),
        )
        for index, outcome in enumerate(cases):
            with self.subTest(index=index):
                self.store.reset_mock()
                self.store.reserve_command.return_value = command_record(id=index + 1)
                target = patch("wqb_cli.agent.runner.subprocess.run", side_effect=outcome) if isinstance(outcome, BaseException) else patch("wqb_cli.agent.runner.subprocess.run", return_value=outcome)
                with target as run, self.assertRaises(RunnerError) as raised:
                    self.runner.run(
                        f"run-{index}", WorkflowNode.J, ("sim", "get", "SIM1"), "result.json"
                    )
                run.assert_called_once()
                self.store.fail_command.assert_called_once()
                rendered = repr((raised.exception, self.store.mock_calls))
                self.assertNotIn("stderr-secret", rendered)
                self.assertNotIn("oserror-secret", rendered)

    def test_ledger_terminal_and_unknown_statuses_fail_closed(self) -> None:
        for status in ("FAILED", "CANCELLED", "mystery"):
            with self.subTest(status=status):
                self.store.reserve_command.return_value = command_record(status=status)
                with patch("wqb_cli.agent.runner.subprocess.run") as run, self.assertRaises(RunnerError):
                    self.runner.run("run", WorkflowNode.J, ("sim", "get", "SIM1"), "x.json")
                run.assert_not_called()
        self.store.reserve_command.return_value = command_record(status="COMPLETED", artifact_id=None)
        with patch("wqb_cli.agent.runner.subprocess.run") as run, self.assertRaises(RunnerError):
            self.runner.run("run", WorkflowNode.J, ("sim", "get", "SIM1"), "x.json")
        run.assert_not_called()

    def test_alpha_submit_recovery_never_submits_and_requires_resource(self) -> None:
        self.store.reserve_command.return_value = command_record(
            status="RECOVERY_REQUIRED", resource_id="ALPHA1"
        )
        completed = subprocess.CompletedProcess([], 0, '{"id":"ALPHA1"}', "")
        with patch("wqb_cli.agent.runner.subprocess.run", return_value=completed) as run:
            self.runner.run(
                "run", WorkflowNode.M, ("alpha", "submit", "ALPHA1"), "result.json"
            )
        self.assertEqual(run.call_args.args[0][-3:], ["alpha", "get", "ALPHA1"])
        self.assertNotIn("submit", run.call_args.args[0])

        self.store.reserve_command.return_value = command_record(
            status="RECOVERY_REQUIRED", resource_id=None
        )
        with patch("wqb_cli.agent.runner.subprocess.run") as run, self.assertRaises(RunnerError):
            self.runner.run("run", WorkflowNode.M, ("alpha", "submit", "A1"), "x.json")
        run.assert_not_called()

    def test_external_allowlist_and_configured_entrypoint(self) -> None:
        executable = self.root / "arxiv-tool.exe"
        executable.write_bytes(b"tool")
        runner = AgentRunner(
            self.store,
            AgentPolicy(Budget()),
            ArtifactWriter(self.root / "artifacts"),
            arxiv_executable=executable,
        )
        completed = subprocess.CompletedProcess([], 0, '{"items":[]}', "")
        with patch("wqb_cli.agent.runner.subprocess.run", return_value=completed) as run:
            runner.run_external(
                "run", WorkflowNode.G, ("arxiv", "search", "query", "factors"), "result.json"
            )
        self.assertEqual(run.call_args.args[0], [str(executable.resolve()), "search", "query", "factors"])

        executable.write_bytes(b"replaced-tool")
        with patch("wqb_cli.agent.runner.subprocess.run") as process, self.assertRaises(RunnerError):
            runner.run_external(
                "run-2", WorkflowNode.G, ("arxiv", "search", "query", "factors"), "result.json"
            )
        process.assert_not_called()

        forbidden = (
            (WorkflowNode.F, ("arxiv", "search", "query", "x")),
            (WorkflowNode.G, ("python", "-c", "print(1)")),
            (WorkflowNode.G, ("arxiv", "download", "x")),
        )
        for node, argv in forbidden:
            with self.subTest(argv=argv), patch("wqb_cli.agent.runner.subprocess.run") as process:
                with self.assertRaises(PolicyViolation):
                    runner.run_external("run", node, argv, "x.json")
                process.assert_not_called()

        with self.assertRaises(RunnerError):
            AgentRunner(
                self.store,
                AgentPolicy(Budget()),
                ArtifactWriter(self.root / "interpreter-artifacts"),
                arxiv_executable=os.sys.executable,
            )

        with self.assertRaises(RunnerError):
            AgentRunner(
                self.store,
                AgentPolicy(Budget()),
                ArtifactWriter(self.root / "relative-artifacts"),
                arxiv_executable="arxiv-tool.exe",
            )

    def test_resource_marking_uses_command_specific_identity_before_completion(self) -> None:
        cases = (
            (("sim", "create"), {"simulation_id": "SIM1", "id": "wrong"}, "SIM1"),
            (("alpha", "submit", "A1"), {"alpha_id": "ALPHA1", "id": "wrong"}, "ALPHA1"),
        )
        for index, (argv, payload, expected) in enumerate(cases):
            with self.subTest(argv=argv):
                self.store.reset_mock()
                self.store.reserve_command.return_value = command_record(id=40 + index)
                completed = subprocess.CompletedProcess([], 0, json.dumps(payload), "")
                with patch("wqb_cli.agent.runner.subprocess.run", return_value=completed):
                    node = WorkflowNode.J if argv[0] == "sim" else WorkflowNode.M
                    self.runner.run(f"run-{index}", node, argv, "result.json")
                mark_index = next(
                    i for i, call in enumerate(self.store.mock_calls) if call[0] == "mark_command_resource"
                )
                complete_index = next(
                    i for i, call in enumerate(self.store.mock_calls) if call[0] == "complete_command"
                )
                self.assertLess(mark_index, complete_index)
                self.store.mark_command_resource.assert_called_once_with(40 + index, expected)


class AgentRunnerStoreIntegrationTests(unittest.TestCase):
    def test_real_store_reuses_completed_result_and_preserves_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = AgentStore(root / "agent.sqlite3")
            store.initialize()
            store.create_run("run", RunConfig(scope_mode=ScopeMode.AUTO))
            runner = AgentRunner(store, AgentPolicy(Budget()), ArtifactWriter(root / "artifacts"))
            completed = subprocess.CompletedProcess([], 0, '{"ok":true}', "")
            with patch("wqb_cli.agent.runner.subprocess.run", return_value=completed) as process:
                first = runner.run(
                    "run", WorkflowNode.J, ("sim", "get", "SIM1"), "result.json"
                )
                second = runner.run(
                    "run", WorkflowNode.J, ("sim", "get", "SIM1"), "result.json"
                )
            self.assertFalse(first.reused)
            self.assertTrue(second.reused)
            self.assertEqual(second.payload, {"ok": True})
            process.assert_called_once()
            ledger = store.reserve_command(
                "run",
                WorkflowNode.J,
                command_fingerprint(WorkflowNode.J, ("sim", "get", "SIM1")),
                ("sim", "get", "SIM1"),
            )
            self.assertEqual(ledger.status, "COMPLETED")
            self.assertEqual(ledger.artifact_id, first.artifact.id)

    def test_real_store_artifacts_ledger_and_result_do_not_persist_fake_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = AgentStore(root / "agent.sqlite3")
            store.initialize()
            store.create_run("run", RunConfig(scope_mode=ScopeMode.AUTO))
            runner = AgentRunner(store, AgentPolicy(Budget()), ArtifactWriter(root / "artifacts"))
            argv = (
                "sim",
                "get",
                "SIM1",
                "--client-secret",
                "argv-fake-secret",
                "--access-token=token-fake-secret",
                "--private-key",
                "key-fake-secret",
            )
            completed = subprocess.CompletedProcess(
                [], 0, '{"api_key":"payload-fake-secret","ok":true}', ""
            )
            with patch("wqb_cli.agent.runner.subprocess.run", return_value=completed) as process:
                result = runner.run("run", WorkflowNode.J, argv, "result.json")
            self.assertEqual(result.payload["api_key"], "[REDACTED]")
            self.assertIn("argv-fake-secret", process.call_args.args[0])
            ledger = store.reserve_command(
                "run", WorkflowNode.J, command_fingerprint(WorkflowNode.J, argv), argv
            )
            self.assertNotIn("argv-fake-secret", repr(ledger))
            persisted = (root / "agent.sqlite3").read_bytes() + b"".join(
                path.read_bytes() for path in (root / "artifacts").rglob("*") if path.is_file()
            )
            self.assertNotIn(b"argv-fake-secret", persisted)
            self.assertNotIn(b"token-fake-secret", persisted)
            self.assertNotIn(b"key-fake-secret", persisted)
            self.assertNotIn(b"payload-fake-secret", persisted)


if __name__ == "__main__":
    unittest.main()
