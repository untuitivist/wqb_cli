# Agent Authentication Redaction Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Node A accept a valid sanitized HTTP 200 authentication response while pausing safely for HTTP 204, 401, and 403 responses.

**Architecture:** Keep authentication classification inside `DiscoveryNodes`. Explicit authentication booleans remain authoritative; otherwise a nonblank `user.id` is the only identity signal needed after transport success, so secret token contents remain redacted and unused.

**Tech Stack:** Python 3.11+, dataclasses, unittest/pytest, existing deterministic fake runner tests.

---

### Task 1: Correct Node A Authentication Classification

**Files:**
- Modify: `tests/test_agent_discovery_nodes.py`
- Modify: `agent/nodes/discovery.py`

- [ ] **Step 1: Add failing regression tests**

Replace the live-token-specific test with the sanitized response and add the 204 case:

```python
def test_a_accepts_authenticated_user_after_token_redaction(self) -> None:
    runner = Mock()
    runner.run.return_value.payload = {
        "ok": True,
        "request": {"method": "GET", "path": "/authentication"},
        "response": {
            "status_code": 200,
            "body": {
                "permissions": ["MULTI_SIMULATION"],
                "token": "[REDACTED]",
                "user": {"id": "fixture-user"},
            },
        },
    }

    result = DiscoveryNodes(
        runner=runner, router=Mock(), store=Mock()
    ).run_a("run-1")

    self.assertIsNone(result.run_state)
    self.assertEqual(result.next_node, WorkflowNode.B)

def test_a_pauses_for_no_content_authentication_response(self) -> None:
    runner = Mock()
    runner.run.return_value.payload = {
        "ok": True,
        "response": {"status_code": 204, "body": ""},
    }

    result = DiscoveryNodes(
        runner=runner, router=Mock(), store=Mock()
    ).run_a("run-1")

    self.assertEqual(result.run_state, RunState.NEEDS_AUTH)
    self.assertIsNone(result.next_node)
```

Keep malformed identity coverage, but remove token-expiry requirements. Test empty or missing user IDs instead:

```python
def test_a_pauses_for_missing_or_malformed_user_identity(self) -> None:
    for body in (
        {"user": {}},
        {"user": {"id": ""}},
        {"user": {"id": 123}},
        {"token": "[REDACTED]"},
    ):
        with self.subTest(body=body):
            runner = Mock()
            runner.run.return_value.payload = {
                "ok": True,
                "response": {"status_code": 200, "body": body},
            }
            result = DiscoveryNodes(
                runner=runner, router=Mock(), store=Mock()
            ).run_a("run-1")
            self.assertEqual(result.run_state, RunState.NEEDS_AUTH)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
python -m pytest tests/test_agent_discovery_nodes.py -k "token_redaction or no_content or user_identity" -v
```

Expected: the redacted-token test fails because Node A requires `token.expiry`; the 204 test fails with `DiscoveryError`.

- [ ] **Step 3: Implement the minimal classification change**

Update `run_a` so unauthenticated transport statuses pause without parsing an empty body:

```python
if status in {204, 401, 403}:
    authenticated = False
else:
    body = self._successful_body(payload)
    authenticated = self._authentication_state(body)
```

Replace `_authenticated` with identity-only validation:

```python
@staticmethod
def _authenticated(body: dict[str, Any]) -> bool:
    if body.get("authenticated") is True or body.get("is_authenticated") is True:
        return True
    user = body.get("user")
    return (
        type(user) is dict
        and type(user.get("id")) is str
        and bool(user["id"].strip())
    )
```

Do not change `_authentication_state` ordering: explicit boolean false must continue to override other fields.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_agent_discovery_nodes.py tests/test_agent_coordinator.py -q
```

Expected: PASS.

- [ ] **Step 5: Run the complete offline suite**

Run:

```powershell
python -m pytest tests -q
python -m compileall -q agent tests
git diff --check
```

Expected: all tests pass, compilation succeeds, and diff check reports no errors.

- [ ] **Step 6: Commit**

```powershell
git add agent/nodes/discovery.py tests/test_agent_discovery_nodes.py
git commit -m "fix(agent): accept sanitized authentication status"
```
