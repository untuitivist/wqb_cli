# `wqb evidence` — external research evidence

`wqb evidence` is the provider-neutral boundary between WQB research workflows and
external financial data. BRAIN remains authoritative for datafield definitions,
simulation semantics, checks, and submission. External providers can only produce
versioned `EvidenceRecord` observations consumed by the research workflow.

## Wind runtime

Check the local Wind Skill without inspecting or printing an API key:

```powershell
wqb evidence wind status
```

The command locates `wind-mcp-skill`, confirms Node.js is available, and computes a
content fingerprint over the installed routing/CLI/reference contract. A WQB run can
lock that fingerprint with `--run-id`; if the automatically updating Wind Skill changes
mid-run, further calls stop with provider-contract drift instead of silently changing
research semantics.

Workflow Wind calls are admitted only through a bounded plan. The legacy
`wqb evidence wind call ...` entrypoint fails closed with
`unplanned_wind_call_forbidden`; it cannot bypass freeze, calibration, fresh balance,
budget, provider-lock, or replay-journal gates.

Allowed standing:

- `G`: primary research / reality checks
- `H`: bounded clarification / reality checks
- `K`: diagnosis only
- `F/I/J/L/M`: Wind calls are rejected

The Wind CLI is invoked using its documented command contract:

```text
node scripts/cli.mjs call <server_type> <tool_name> @scripts/request-<unique>.json
```

The unique parameter file is always removed after the call. `WIND_API_KEY` remains in
the Wind Skill's own supported configuration path/environment and is never copied into
an EvidenceRecord.

## Evidence record

Every admitted call stores:

- provider and exact `server_type.tool_name`
- complete request parameters
- retrieval time, entity identifiers, as-of/period semantics
- raw Wind envelope and SHA-256
- normalized `content[0].text`
- units, provider sources and update dates when returned
- `cli_meta` warnings/completeness
- Wind contract content fingerprint
- supported mechanism ids and explicit limitations

Wind error envelopes and route mismatches are not admitted as evidence.

Records are immutable under `local/evidence/records/` and can be verified with:

```powershell
wqb evidence verify <record.json>
```

## Paired-research freeze

Before any G/H Wind treatment, freeze the exact pre-treatment research universe:

```powershell
wqb evidence experiment freeze `
  --run-id <RUN_ID> `
  --main-tower <D>/main_tower.json `
  --candidate-datafields <F>/candidate_datafields.json `
  --mechanisms <G>/mechanism_families.json `
  --run-constraints <run>/run_constraints.json `
  --brain-field-snapshot <G>/field_meta__field_a.json `
  --brain-field-snapshot <G>/field_meta__field_b.json `
  --non-wind-evidence <G>/evidence_index.json `
  --output <run>/research_freeze.json
```

`candidate_datafields.json` must explicitly declare `freeze_status=FROZEN`,
`complete=true`, and `scope_pending=false`. Every frozen candidate must be covered by a
BRAIN metadata snapshot, every mechanism family must use only frozen F fields, and the
pre-Wind mechanism families must not already contain Wind reality evidence. The manifest
hashes every artifact and is revalidated before `plan-check`, `execute-plan`, and
`plan-status`. Its SHA-256 is part of the research `plan_id`, so identical requests under
a different frozen universe cannot reuse the same journal.

Verify a freeze without sending any provider request:

```powershell
wqb evidence experiment freeze-verify --input <run>/research_freeze.json
```

## Balance observations

The budget gate does not treat the advertised daily grant as a runtime balance. Record an
authoritative Alice Market account reading instead:

```powershell
wqb evidence balance add wind --available-points 970 --source alice_market_account
wqb evidence balance latest wind
```

A real `wind execute-plan` always uses the latest recorded Wind balance; an inline
`available_points` value is ignored during execution. By default the recorded observation
must be no more than 30 minutes old (`balance_max_age_seconds` can make the contract
stricter or looser). `wind plan-check` may still use inline `available_points` for a
controlled/dry-run admission estimate, where it is labeled `plan_inline`. This lets one
plan file be checked hypothetically without allowing that hypothetical number to fund a
real provider call.

## Point-cost calibration

WQB does not hard-code the daily free grant or assume a per-tool price. Record actual
before/after balances observed in Alice Market:

```powershell
wqb evidence cost add stock_data.get_stock_fundamentals `
  --before 1000 --after 980 --success
```

Build p50/p95 profiles. A plan is not considered calibrated until the selected cost profile has at least **3 successful samples**. By default only successful observations from the last **7 days** are eligible; historical-only calibration is reported as `stale_cost_profile`:

```powershell
wqb evidence cost profile
```

Gate a planned research batch using current available points and p95 cost:

```powershell
wqb evidence cost gate `
  --available-points 1000 `
  --purpose research `
  --plan '{"stock_data.get_stock_fundamentals":2,"economic_data.query_economic_indicator_data":1}'
```

Default allocations are deliberately conservative: 60% research, 20% diagnosis, 20%
reserve. They are WQB policy, not Wind pricing.

For a G/H reality-check plan, `wind plan-check` is mandatory. Research plans require a
validated `run_id + freeze_manifest`; the plan contract allows at most 6 research
mechanisms and at most 3 Wind calls per mechanism. K diagnosis allows at most 3 calls
total and does not consume the paired-research freeze. Research and diagnosis budgets
cannot be mixed in one plan. `analytics_data` is rejected by default because it can be
materially more expensive than specialist routes; a check must set
`allow_expensive_fallback: true` and a non-empty `fallback_reason` explaining why the
specialist domain cannot express the required observation.

## Resumable plan execution

After `wind plan-check` passes, execute the admitted checks as one serialized run instead
of manually looping over `wind call`:

```powershell
wqb evidence wind execute-plan `
  --input <node_dir>/wind_reality_plan.json `
  --output <node_dir>/reality_evidence_index.json
```

Executable checks add `check_id` and `params` (plus optional entity/time/provenance
fields) to the plan:

```json
{
  "run_id": "RUN-2026-09-07-CHN-FUNDAMENTAL-01",
  "freeze_manifest": "../research_freeze.json",
  "balance_max_age_seconds": 1800,
  "checks": [
    {
      "check_id": "quality-roe-600519",
      "mechanism_id": "quality-1",
      "node": "G",
      "purpose": "research",
      "server_type": "stock_data",
      "tool_name": "get_stock_fundamentals",
      "cost_profile_key": "stock_data.get_stock_fundamentals:single",
      "params": {"question": "600519.SH 2024 ROE"},
      "entity_ids": {"windcode": "600519.SH"},
      "supports": ["mechanism:quality-1"]
    }
  ]
}
```

For an optional dry `plan-check`, the same JSON may temporarily include
`"available_points": 970`; `execute-plan` will ignore it and require the fresh balance
ledger instead.

Execution is serial and journaled under `local/evidence/runs/<RUN_ID>/`. Each
`completed[]` result includes both the immutable `evidence_id` and absolute `stored_path`,
so downstream nodes can run `wqb evidence verify <stored_path>` without reconstructing the
EvidenceStore layout. `plan-status` exposes the same path after verifying the record.
Completed `check_id`s are verified and skipped on resume. If WQB knows a request was started but
cannot establish an authoritative terminal result (timeout, non-JSON response, provider
contract drift during the call, etc.), the journal becomes `outcome_unknown` and the
same plan **must not blindly replay that check**. Resolve the external state first or
create an explicit replacement plan after reconciliation.
