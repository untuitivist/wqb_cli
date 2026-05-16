# A Login / Shared Auth

## Role

Verify that the active run has usable WQB authentication context.
This node is executed by a nodesubagent only.

## Required Inputs

- `node_input.json`
- Repo-local auth configuration may be read, but no auth files may be modified by this node unless the user explicitly requested login refresh.

## Required Outputs

- `outputs/auth_status.json`
- `process_log.md`
- `evidence_index.json`
- `validation_report.json`
- `handoff.md`
- `node_result.json`

## Process Requirements

1. Inspect whether authentication state is present and usable.
2. Record the exact non-secret evidence used.
3. Do not print or copy credentials, cookies, or tokens into outputs.
4. If auth is missing or expired, return `status=blocked`.
5. Prefer the source script:
   `python wqb_core/user/get_authentication.py --output outputs/auth_status.json`

## Success Criteria

- `outputs/auth_status.json` states whether auth is usable.
- No secret material appears in any output.

## Block Conditions

- Authentication is unavailable.
- A required login refresh would write outside the assigned node directory.
