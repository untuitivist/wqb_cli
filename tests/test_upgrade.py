from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import requests

from wqb_cli.cli import build_parser
from wqb_cli.commands.upgrade import handle_upgrade
from wqb_cli.core.upgrade import (
    API_ROOT, RELEASE_ROOT, GitHubAuth, UpgradeError, _apply_job, _environment, _fetch, _github_token, _install,
    _wheel_requirements, _windows_launcher, release_version, upgrade, upgrade_status,
)


def response(content: bytes, status: int = 200, **headers: str) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result.raw = io.BytesIO(content)
    result.headers.update(headers)
    return result


def release_fixture(version: str = "0.6.4", *, metadata: bytes | None = None) -> tuple[dict, bytes, bytes]:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(f"wqb_cli-{version}.dist-info/METADATA", metadata or
                         f"Metadata-Version: 2.1\nName: wqb-cli\nVersion: {version}\nRequires-Python: >=3.11\n".encode())
    wheel = buffer.getvalue()
    wheel_name = f"wqb_cli-{version}-py3-none-any.whl"
    checksums = f"{hashlib.sha256(wheel).hexdigest()}  {wheel_name}\n".encode()
    release = {"tag_name": f"v{version}", "draft": False, "prerelease": False, "assets": [
        {"name": name, "state": "uploaded", "browser_download_url": f"{RELEASE_ROOT}/download/v{version}/{name}",
         "digest": "sha256:" + hashlib.sha256(content).hexdigest()}
        for name, content in ((wheel_name, wheel), ("SHA256SUMS.txt", checksums))
    ]}
    return release, checksums, wheel


class UpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock()
        self.session.__enter__.return_value = self.session
        self.session_patch = patch("wqb_cli.core.upgrade.requests.Session", return_value=self.session)
        self.session_patch.start()
        self.addCleanup(self.session_patch.stop)
        self.version_patch = patch("wqb_cli.core.upgrade.__version__", "0.6.3")
        self.version_patch.start()
        self.addCleanup(self.version_patch.stop)
        token_patch = patch("wqb_cli.core.upgrade._github_token", return_value=None)
        token_patch.start()
        self.addCleanup(token_patch.stop)
        launcher_patch = patch("wqb_cli.core.upgrade._windows_launcher", return_value=False)
        launcher_patch.start()
        self.addCleanup(launcher_patch.stop)

    def fixture(self, version: str = "0.6.4", **kwargs) -> tuple[dict, bytes, bytes]:
        release, checksums, wheel = release_fixture(version, **kwargs)
        self.session.get.side_effect = [response(json.dumps(release).encode()), response(checksums), response(wheel)]
        return release, checksums, wheel

    def test_check_selects_latest_without_install_or_account_auth(self) -> None:
        self.fixture()
        with patch("wqb_cli.core.upgrade._environment") as environment, patch("wqb_cli.core.upgrade._install") as install:
            result = upgrade(check=True)
        self.assertEqual(result["status"], "update_available")
        self.assertFalse(result["installed"])
        self.assertEqual(self.session.get.call_count, 1)
        self.assertEqual(self.session.get.call_args.args[0], API_ROOT + "/releases/latest")
        self.assertFalse(self.session.get.call_args.kwargs["allow_redirects"])
        self.assertNotIn("auth", self.session.get.call_args.kwargs)
        environment.assert_not_called()
        install.assert_not_called()

    def test_dry_run_exact_version_does_not_download_wheel(self) -> None:
        self.fixture()
        result = upgrade(target_version="v0.6.4", dry_run=True)
        self.assertEqual(result["status"], "planned")
        self.assertEqual(self.session.get.call_args.args[0], API_ROOT + "/releases/tags/v0.6.4")
        self.assertEqual(self.session.get.call_count, 1)

    def test_latest_older_than_installed_never_downgrades(self) -> None:
        self.fixture("0.6.1")
        with patch("wqb_cli.core.upgrade._install") as install:
            result = upgrade(allow_downgrade=True, reinstall=True)
        self.assertEqual(result["status"], "installed_newer_than_latest")
        install.assert_not_called()

    def test_explicit_downgrade_requires_opt_in(self) -> None:
        self.fixture("0.6.1")
        with self.assertRaises(UpgradeError) as caught:
            upgrade(target_version="0.6.1")
        self.assertEqual(caught.exception.reason, "downgrade_blocked")
        self.assertFalse(caught.exception.as_dict()["ok"])

    def test_explicit_downgrade_can_be_previewed_with_opt_in(self) -> None:
        self.fixture("0.6.1")
        result = upgrade(target_version="0.6.1", allow_downgrade=True, check=True)
        self.assertEqual(result["status"], "downgrade_available")

    def test_same_version_is_no_op_unless_reinstall_requested(self) -> None:
        self.fixture("0.6.3")
        self.assertEqual(upgrade()["status"], "up_to_date")
        self.fixture("0.6.3")
        self.assertEqual(upgrade(reinstall=True, check=True)["status"], "reinstall_available")

    def test_verified_bytes_are_installed_only_after_checks_pass(self) -> None:
        _, _, wheel_bytes = self.fixture()

        def installed(wheel, version):
            self.assertEqual(wheel.read_bytes(), wheel_bytes)
            self.assertEqual(version, "0.6.4")
            return {"verification": {"runtime": version}}

        with patch("wqb_cli.core.upgrade._environment") as environment, patch("wqb_cli.core.upgrade._install", side_effect=installed) as install:
            result = upgrade()
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["sha256"], hashlib.sha256(wheel_bytes).hexdigest())
        environment.assert_called_once()
        install.assert_called_once()

    def test_native_windows_launch_defers_install_until_launcher_exits(self) -> None:
        _, _, expected = self.fixture()

        def start_job(wheel, version, digest, result, output):
            self.assertEqual(wheel.read_bytes(), expected)
            self.assertEqual(version, "0.6.4")
            self.assertEqual(output, "receipt.json")
            return {**result, "status": "upgrade_started", "installed": False}

        with patch("wqb_cli.core.upgrade._windows_launcher", return_value=True), \
                patch("wqb_cli.core.upgrade._environment"), patch("wqb_cli.core.upgrade._install") as install, \
                patch("wqb_cli.core.upgrade._start_windows_job", side_effect=start_job):
            result = upgrade(output="receipt.json")
        self.assertEqual(result["status"], "upgrade_started")
        self.assertFalse(result["installed"])
        install.assert_not_called()

    def test_tampered_wheel_is_rejected_before_pip(self) -> None:
        release, checksums, _ = self.fixture()
        self.session.get.side_effect = [response(json.dumps(release).encode()), response(checksums), response(b"tampered")]
        with patch("wqb_cli.core.upgrade._environment"), patch("wqb_cli.core.upgrade._install") as install:
            with self.assertRaises(UpgradeError) as caught:
                upgrade()
        self.assertEqual(caught.exception.reason, "wheel_checksum_mismatch")
        install.assert_not_called()

    def test_checksum_manifest_digest_mismatch_is_rejected(self) -> None:
        release, checksums, wheel = self.fixture()
        self.session.get.side_effect = [response(json.dumps(release).encode()), response(checksums + b"changed"), response(wheel)]
        with patch("wqb_cli.core.upgrade._environment"), self.assertRaises(UpgradeError) as caught:
            upgrade()
        self.assertEqual(caught.exception.reason, "asset_digest_mismatch")
        self.assertEqual(self.session.get.call_count, 2)

    def test_duplicate_checksum_or_asset_is_rejected(self) -> None:
        for duplicate_asset in (False, True):
            with self.subTest(duplicate_asset=duplicate_asset):
                release, checksums, wheel = release_fixture()
                if duplicate_asset:
                    release["assets"].append(release["assets"][0])
                else:
                    checksums += checksums
                    release["assets"][1]["digest"] = None
                self.session.get.side_effect = [response(json.dumps(release).encode()), response(checksums), response(wheel)]
                with patch("wqb_cli.core.upgrade._environment"), patch("wqb_cli.core.upgrade._install") as install:
                    with self.assertRaises(UpgradeError):
                        upgrade()
                install.assert_not_called()

    def test_unpublished_or_mismatched_release_is_rejected(self) -> None:
        for change in ({"draft": True}, {"prerelease": True}, {"tag_name": "v0.6.5"}, {"assets": []}):
            with self.subTest(change=change):
                release, _, _ = release_fixture()
                release.update(change)
                self.session.get.side_effect = [response(json.dumps(release).encode())]
                with self.assertRaises(UpgradeError):
                    upgrade(target_version="0.6.4", check=True)

    def test_untrusted_asset_url_is_rejected_even_in_check_mode(self) -> None:
        release, _, _ = release_fixture()
        release["assets"][0]["browser_download_url"] = "https://example.com/payload.whl"
        self.session.get.side_effect = [response(json.dumps(release).encode())]
        with self.assertRaises(UpgradeError) as caught:
            upgrade(check=True)
        self.assertEqual(caught.exception.reason, "invalid_release_asset")

    def test_version_is_numeric_and_not_shell_or_url_input(self) -> None:
        self.assertEqual(release_version("v0.6.10"), "0.6.10")
        for value in ("../master", "0.6.3;exit", "0.6.3rc1", "0.6.3+local", "https://example.com", "01.2.3"):
            with self.subTest(value=value), self.assertRaises(UpgradeError):
                upgrade(target_version=value, check=True)
        self.session.get.assert_not_called()
        self.fixture("0.6.10")
        self.assertTrue(upgrade(check=True)["update_available"])

    def test_release_404_and_throttle_are_structured_without_retrying(self) -> None:
        for status in (404, 403, 429):
            with self.subTest(status=status):
                self.session.get.side_effect = [response(b"error", status, **{"Retry-After": "60"})]
                args = build_parser(plugins=[]).parse_args(["upgrade", "--check"])
                with patch("wqb_cli.commands.upgrade.write_json") as write:
                    self.assertEqual(handle_upgrade(args), 1)
                self.assertEqual(write.call_args.args[0]["http_status"], status)
                self.assertEqual(write.call_args.args[0]["reason"], "release_http_error")

    def test_network_failure_is_structured(self) -> None:
        self.session.get.side_effect = requests.Timeout("fixture")
        args = build_parser(plugins=[]).parse_args(["upgrade", "--output", "result.json"])
        with patch("wqb_cli.commands.upgrade.write_json") as write:
            self.assertEqual(handle_upgrade(args), 1)
        self.assertEqual(write.call_args.args[0]["reason"], "release_network_error")
        self.assertEqual(write.call_args.args[1], "result.json")


class DownloadAndInstallTests(unittest.TestCase):
    def test_github_token_is_sent_only_to_the_api_origin(self) -> None:
        auth = GitHubAuth("private-fixture-token")
        for address in (API_ROOT + "/releases/latest", RELEASE_ROOT + "/download/v0.6.3/file.whl",
                        "https://release-assets.githubusercontent.com/file", "https://api.worldquantbrain.com/authentication",
                        "http://api.github.com/releases", "https://api.github.com:444/releases"):
            request = requests.Request("GET", address).prepare()
            auth(request)
            self.assertEqual("Authorization" in request.headers, address.startswith("https://api.github.com/"))

    def test_environment_token_precedes_gh_and_is_not_logged(self) -> None:
        with patch.dict("os.environ", {"GH_TOKEN": "fixture", "GITHUB_TOKEN": "other"}), \
                patch("wqb_cli.core.upgrade.subprocess.run") as run:
            self.assertEqual(_github_token(), "fixture")
        run.assert_not_called()

    def test_existing_gh_auth_can_supply_token_without_an_interactive_login(self) -> None:
        with patch.dict("os.environ", {}, clear=True), patch("wqb_cli.core.upgrade.shutil.which", return_value="gh"), \
                patch("wqb_cli.core.upgrade.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="fixture\n")) as run:
            self.assertEqual(_github_token(), "fixture")
        self.assertEqual(run.call_args.args[0], ["gh", "auth", "token", "--hostname", "github.com"])

    def test_redirect_to_untrusted_origin_is_not_requested(self) -> None:
        session = MagicMock()
        session.get.return_value = response(b"", 302, Location="https://example.com/private")
        with self.assertRaises(UpgradeError) as caught:
            _fetch(session, API_ROOT + "/releases/latest", 100)
        self.assertEqual(caught.exception.reason, "untrusted_release_url")
        session.get.assert_called_once()

    def test_https_and_exact_hosts_are_required(self) -> None:
        for address in ("http://github.com/x", "https://github.com.evil.test/x", "https://user:password@github.com/x", "https://github.com:444/x"):
            with self.subTest(address=address), self.assertRaises(UpgradeError):
                _fetch(MagicMock(), address, 100)

    def test_download_size_and_redirect_budgets(self) -> None:
        for replies in ([response(b"a" * 101)], [response(b"", **{"Content-Length": "101"})],
                        [response(b"", 302, Location=API_ROOT + "/loop") for _ in range(6)]):
            session = MagicMock()
            session.get.side_effect = replies
            with self.subTest(replies=len(replies)), self.assertRaises(UpgradeError):
                _fetch(session, API_ROOT + "/releases/latest", 100)

    def test_wheel_metadata_python_and_dependencies_are_checked(self) -> None:
        for fields, reason in (("Name: other\nVersion: 0.6.4\n", "invalid_wheel_metadata"),
                               ("Name: wqb-cli\nVersion: 0.6.4\nRequires-Python: >=99\n", "incompatible_python"),
                               ("Name: wqb-cli\nVersion: 0.6.4\nRequires-Dist: nonexistent-wqb-test-dependency>=1\n", "dependency_requirements_not_met")):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temporary:
                _, _, content = release_fixture(metadata=("Metadata-Version: 2.1\n" + fields).encode())
                wheel = Path(temporary) / "package.whl"
                wheel.write_bytes(content)
                with self.assertRaises(UpgradeError) as caught:
                    _wheel_requirements(wheel, "0.6.4")
                self.assertEqual(caught.exception.reason, reason)

    def test_editable_and_foreign_source_installs_are_rejected(self) -> None:
        distribution = MagicMock()
        distribution.read_text.return_value = '{"dir_info":{"editable":true}}'
        distribution.locate_file.return_value = Path("other/wqb_cli/__init__.py")
        with patch("wqb_cli.core.upgrade.metadata.distribution", return_value=distribution):
            with self.assertRaises(UpgradeError) as caught:
                _environment()
        self.assertEqual(caught.exception.reason, "source_install")

    def test_installer_uses_same_interpreter_no_shell_and_verifies_new_process(self) -> None:
        calls = [SimpleNamespace(returncode=0, stdout="installed", stderr=""),
                 SimpleNamespace(returncode=0, stdout='{"runtime":"0.6.4","metadata":"0.6.4"}', stderr="")]
        with patch("wqb_cli.core.upgrade.subprocess.run", side_effect=calls) as run:
            result = _install(Path("release.whl"), "0.6.4")
        command = run.call_args_list[0].args[0]
        self.assertEqual(command[:6], [__import__("sys").executable, "-I", "-X", "utf8", "-m", "pip"])
        self.assertIn("--no-deps", command)
        self.assertIn("--no-index", command)
        self.assertNotIn("shell", run.call_args_list[0].kwargs)
        self.assertEqual(result["verification"]["runtime"], "0.6.4")

    def test_installer_failure_and_false_success_never_report_updated(self) -> None:
        for calls, reason in (([SimpleNamespace(returncode=1, stdout="", stderr="permission denied")], "installation_failed"),
                              ([SimpleNamespace(returncode=0, stdout="", stderr=""),
                                SimpleNamespace(returncode=0, stdout='{"runtime":"0.6.2","metadata":"0.6.2"}', stderr="")], "installation_verification_failed")):
            with self.subTest(reason=reason), patch("wqb_cli.core.upgrade.subprocess.run", side_effect=calls):
                with self.assertRaises(UpgradeError) as caught:
                    _install(Path("release.whl"), "0.6.4")
                self.assertEqual(caught.exception.reason, reason)

    def test_install_timeout_preserves_partial_installer_output(self) -> None:
        timeout = subprocess.TimeoutExpired(["python", "-m", "pip"], 600, output=b"uninstall started", stderr=b"waiting")
        with patch("wqb_cli.core.upgrade.subprocess.run", side_effect=timeout):
            with self.assertRaises(UpgradeError) as caught:
                _install(Path("release.whl"), "0.6.4")
        self.assertEqual(caught.exception.reason, "installation_timed_out")
        self.assertEqual(caught.exception.evidence["installer"]["stdout"], "uninstall started")


class UpgradeJobTests(unittest.TestCase):
    def test_distlib_launcher_name_is_detected_after_exe_suffix_is_removed(self) -> None:
        for name, expected in (("wqb.exe", True), ("wqb", True), ("__main__.py", False)):
            with self.subTest(name=name), patch("sys.platform", "win32"), patch("sys.argv", [name, "upgrade"]):
                self.assertEqual(_windows_launcher(), expected)

    def test_worker_rechecks_staged_hash_and_preserves_final_status(self) -> None:
        for tamper in (False, True):
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                _, _, content = release_fixture()
                wheel = directory / "wqb_cli-0.6.4-py3-none-any.whl"
                wheel.write_bytes(content + (b"tampered" if tamper else b""))
                job = {"wheel": str(wheel), "version": "0.6.4", "sha256": hashlib.sha256(content).hexdigest(),
                       "launcher_pid": 123, "output": str(directory / "output.json")}
                job_path = directory / "job.json"
                job_path.write_text(json.dumps(job), encoding="utf-8")
                (directory / "result.json").write_text('{"ok":true,"status":"upgrade_started","installed":false,"job_pid":456}', encoding="utf-8")
                with patch("wqb_cli.core.upgrade._wait_process", return_value=True), \
                        patch("wqb_cli.core.upgrade._environment"), patch("wqb_cli.core.upgrade._install", return_value={"verification": {"runtime": "0.6.4"}}) as install:
                    code = _apply_job(job_path)
                result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
                self.assertEqual(result, json.loads((directory / "output.json").read_text(encoding="utf-8")))
                self.assertEqual(result["job_pid"], 456)
                self.assertEqual(code, 1 if tamper else 0)
                if tamper:
                    self.assertEqual(result["reason"], "wheel_checksum_mismatch")
                    install.assert_not_called()
                else:
                    self.assertEqual(result["status"], "updated")
                    self.assertTrue(result["installed"])

    def test_status_wait_blocks_on_process_handle_then_reads_final_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "result.json"
            receipt.write_text('{"ok":true,"status":"upgrade_started","installed":false,"job_pid":123}', encoding="utf-8")

            def complete(process_id):
                self.assertEqual(process_id, 123)
                receipt.write_text('{"ok":true,"status":"updated","installed":true}', encoding="utf-8")
                return True

            with patch("wqb_cli.core.upgrade._wait_process", side_effect=complete):
                self.assertEqual(upgrade_status(str(receipt), wait=True)["status"], "updated")

    def test_missing_worker_outcome_is_not_reported_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "result.json"
            receipt.write_text('{"ok":true,"status":"upgrade_started","installed":false,"job_pid":123}', encoding="utf-8")
            with patch("wqb_cli.core.upgrade._wait_process", return_value=True):
                result = upgrade_status(str(receipt), wait=True)
            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "upgrade_job_ended_without_receipt")


if __name__ == "__main__":
    unittest.main()
