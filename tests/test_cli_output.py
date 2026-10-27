from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wqb_cli.cli import build_parser, handle_auth


class AuthOutputTests(unittest.TestCase):
    def test_auth_commands_save_native_response_in_requested_file(self) -> None:
        for command in ("status", "head", "login", "logout", "brainlabs", "persona", "support", "workday"):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "auth.json"
                args = build_parser(plugins=[]).parse_args(["auth", command, "--output", str(target)])
                reply = {"ok": True, "response": {"status_code": 200}}
                with patch("wqb_cli.cli.WqbClient") as client, patch("wqb_cli.cli.session_from_cookies"), \
                        patch("wqb_cli.cli.resolve_login_payload", return_value={}), patch("wqb_cli.cli.save_cookie_payload"):
                    client.return_value.call.return_value = reply
                    self.assertEqual(handle_auth(args), 0)
                self.assertEqual(json.loads(target.read_text(encoding="utf-8")), reply)


if __name__ == "__main__":
    unittest.main()
