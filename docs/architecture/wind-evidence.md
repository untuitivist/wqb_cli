# Wind evidence architecture

## Standing

Wind is an **external structured reality-evidence provider**. It is not an alternate
BRAIN datafield source and never becomes the authority for simulation, checks, or Alpha
submission.

```text
BRAIN field metadata ─┐
community / papers ───┼─> G evidence package ─> H mechanism contract ─> I expression
Wind reality evidence ┘                                         │
                                                                v
                                                        J BRAIN simulation
                                                                │
                                                                v
                                                   K diagnosis (+ bounded Wind)
```

Hard call standing:

| Node | Wind standing | Purpose |
| --- | --- | --- |
| F | forbidden | field feasibility remains BRAIN/local-scope only |
| G | primary | reality observation for already shortlisted mechanism families |
| H | supplemental | clarification only; evidence shortage normally returns to G |
| I | forbidden | expression construction must consume contracts, not query providers |
| J | forbidden | simulation remains BRAIN-authoritative |
| K | diagnostic | bounded reality query for mechanism-vs-implementation diagnosis |
| L | forbidden | final correlation/check path remains BRAIN-authoritative |
| M | forbidden | submission never queries external providers |

## Provider contract lock

The Wind Skill updates automatically, so Git commit metadata cannot be assumed to be
present or stable in every installation. WQB fingerprints the callable local contract:

- `SKILL.md`
- `scripts/cli.mjs`
- `scripts/tool-manifest.json`
- every `references/*.md`

A run locks the fingerprint on its first Wind call. Contract drift during the same run
is a hard stop. A later run can intentionally accept the newer fingerprint.

## Evidence strength

`EvidenceRecord` proves what Wind returned under a particular provider contract at a
particular retrieval time. It does **not** by itself prove market-wide completeness or
convert a provider observation into Alpha performance evidence.

Recommended standing inside H:

1. `BRAIN_FIELD_METADATA` — authoritative for the field actually available to Alpha.
2. `PRIMARY_DOCUMENT` — issuer/exchange/statistical authority text where directly cited.
3. `WIND_REALITY_OBSERVATION` — structured real-market observation and provider metadata.
4. `ACADEMIC_MECHANISM` — mechanism theory/empirical literature.
5. `COMMUNITY_EXPERIENCE` — implementation ideas and failure patterns.
6. `BACKTEST_EVIDENCE` — BRAIN simulation result for the specific expression/settings.

These categories support different claims and must not be collapsed into one confidence
score.

## Paired-research admission freeze

G/H research Wind calls are not admitted from an unfrozen candidate universe. Before the
paired split, WQB hashes and validates the exact `main_tower.json`, final F
`candidate_datafields.json`, pre-Wind `mechanism_families.json`, run constraints, every
candidate's BRAIN field metadata snapshot, and any pre-existing non-Wind evidence. Final F
must explicitly declare `freeze_status=FROZEN`, `complete=true`, and
`scope_pending=false`.

The resulting `research_freeze.json` binds every mechanism id to F field ids. G/H plans
must carry the same `run_id` and freeze manifest; a mechanism absent from the freeze is a
hard admission failure. The freeze manifest SHA-256 is part of the research `plan_id`, so
the replay journal cannot be reused across different candidate universes. K diagnosis is
not part of this paired pre-treatment freeze.

The legacy raw `wind call` CLI entrypoint fails closed for workflow use. Real calls must
go through `plan-check` and `execute-plan` so freeze, calibration, balance, budget,
provider-contract locking, and no-blind-replay recovery are enforced together.

## Budget contract

The free grant and prices are runtime facts. WQB stores actual `points_before` and
`points_after` observations and derives per-query p50/p95 profiles. Failed/refunded calls
are recorded but excluded from successful cost profiles.

`plan-check` may use an inline point value for a controlled dry estimate. `execute-plan`
ignores inline `available_points` and requires a fresh recorded Alice Market balance; a
hypothetical plan value therefore cannot fund a real provider request.

Default run allocation:

- research: 60% of currently observed available points
- diagnosis: 20%
- reserve: 20%

G/H plans are bounded to at most six mechanisms and three calls per mechanism. K has a
separate maximum of three diagnostic calls. Missing or thin cost profiles (fewer than 3 successful observations) block the plan rather
than being guessed. Successful observations are fresh for 7 days by default; historical-only samples are treated as stale, not silently reused forever. `cost_profile_key` may further split one tool into request-size/width classes so a small probe does not price a wider production query. `analytics_data` is an explicit expensive fallback and requires a recorded reason that specialist Wind routes cannot express the required observation.

## Degradation

Wind is optional evidence, not an execution dependency. Runtime/key/quota/provider errors
must be represented as evidence unavailability and must not mutate BRAIN requests. A G
node cannot claim the Wind portion of its evidence package completed if the required
reality checks were not actually obtained; it may either fall back under an explicitly
allowed workflow rule or remain incomplete. I/J/L/M continue to reject Wind calls even
when another node is blocked.

## Serialized execution and recovery

An admitted reality plan is executed through `wqb evidence wind execute-plan`, not an
Agent-written call loop. The executable plan has stable `check_id`s and is content-hashed
into a `plan_id`. WQB persists the immutable plan plus an append-only journal:

```text
planned -> started -> completed(evidence_id)
                  \-> provider_error
                  \-> runtime_error
                  \-> outcome_unknown
```

A resumed run verifies every previously completed EvidenceRecord and skips the provider
call. `started` without a trustworthy terminal event, or an explicit
`outcome_unknown`, is a hard no-blind-replay stop. This protects both research
provenance and the finite Wind point budget when a network/process interruption occurs
after the request may already have reached the provider.
