# Wind evidence pilot — paired WQB research run

## Question

Does Wind reality evidence improve **research decision quality before expression search**
without making the workflow dependent on Wind for BRAIN execution?

The pilot is not successful merely because one Wind-enabled Alpha has higher Sharpe.

## Cell selection

Use one small `workflow_simu` CHN cell where Wind has plausible information advantage,
preferably a MODEL / analyst / fundamental / quality / valuation mechanism rather than a
pure price-volume cell.

Freeze before splitting arms:

- same D `main_tower.json`
- same final F `candidate_datafields.json` with `freeze_status=FROZEN`, `complete=true`, and `scope_pending=false`
- same pre-Wind `mechanism_families.json` mapping mechanism ids to frozen F fields
- same BRAIN field metadata snapshots covering every frozen candidate
- same community/docs/platform/paper evidence already gathered
- same run-level simulation settings constraints

Materialize those inputs with `wqb evidence experiment freeze` and verify the resulting
`research_freeze.json` before either arm starts. The treatment arm may add only Wind
`EvidenceRecord` observations. It may eliminate or reprioritize frozen fields/mechanisms,
but it must not introduce a BRAIN field or mechanism family absent from the freeze.

## Arms

### Arm A — baseline

Run H without Wind reality evidence, then I/J/K under the normal adaptive workflow.

### Arm B — Wind

Starting from the same frozen F/G non-Wind evidence:

1. group candidates into 3–6 mechanism families;
2. read current Alice Market available points;
3. verify the same `research_freeze.json` used for the paired split;
4. read and record a fresh Alice Market available-points observation;
5. require calibrated p95 profiles for every planned query type;
6. pass `wqb evidence wind plan-check` with the frozen mechanism ids;
7. execute only the approved Wind checks under one `RUN_ID` provider-contract lock; execution ignores any inline balance and uses the fresh ledger observation;
8. produce `reality_checks.json` and the Wind-enabled H contracts;
9. continue to I/J/K with identical BRAIN execution rules.

## Primary outcomes

Before I:

- mechanisms eliminated by the Wind arm;
- `direction_status` changes;
- mechanisms with stronger falsification conditions;
- mechanisms whose reality observations conflict with the original story;
- any illegal mechanism addition (treatment mechanism not present in frozen `mechanism_families.json`) — hard protocol violation;
- any treatment field not present in frozen F — hard protocol violation.

Use:

```powershell
wqb evidence experiment compare `
  --baseline-contracts <armA>/H/mechanism_contracts.json `
  --wind-contracts <armB>/H/mechanism_contracts.json `
  --baseline-candidates <armA>/I/expression_candidates.json `
  --wind-candidates <armB>/I/expression_candidates.json `
  --output <pilot>/mechanism_impact.json
```

After J/K:

- candidate count entering simulation;
- valid simulation completion rate;
- proportion failing for data/unit/mechanism/economic-metric reasons;
- proportion reaching L;
- actual Wind points consumed by query type;
- research wall-clock time.

## Interpretation

Strong positive evidence for productization is **information efficiency**, e.g. Wind
causes weak mechanisms to be rejected or falsification conditions to become sharper
before expensive expression/simulation search, while preserving or improving the share
of candidates reaching later gates.

One lucky high-Sharpe Alpha is not enough. Conversely, a lower candidate count is not a
failure when the removed candidates are precisely those later classified as weak or
incoherent in the baseline arm.

## Stop conditions

Stop and do not productize broadly when:

- provider contract drift cannot be controlled;
- required query types cannot obtain stable cost profiles;
- the treatment arm routinely consumes most daily points before H closes;
- Wind evidence often lacks entity/time/unit/source semantics needed by the mechanism;
- H uses Wind to invent new fields/mechanisms rather than test the frozen F universe;
- repeated pilots show no meaningful change in pre-I decisions or later failure density.

Only after a positive adaptive pilot should Wind be added to `workflow_batchsimu`; iFinD
or other providers remain out of scope until the provider-neutral EvidenceRecord contract
has proved useful with Wind.

## Machine-readable J/K outcome metrics

After both arms reach their K decision, write one small metrics object per arm:

```json
{
  "simulation_attempts": 20,
  "valid_simulations": 14,
  "reached_l": 3,
  "failure_count": 8,
  "wall_clock_seconds": 1000,
  "wind_points_consumed": 0
}
```

Then include them in the paired comparison:

```powershell
wqb evidence experiment compare `
  --baseline-contracts <armA>/H/mechanism_contracts.json `
  --wind-contracts <armB>/H/mechanism_contracts.json `
  --baseline-candidates <armA>/I/expression_candidates.json `
  --wind-candidates <armB>/I/expression_candidates.json `
  --baseline-metrics <armA>/pilot_metrics.json `
  --wind-metrics <armB>/pilot_metrics.json `
  --output <pilot>/paired_impact.json
```

The output includes deltas for valid-simulation rate, failure density, L-gate rate,
wall-clock and actual Wind points. A positive result should therefore be visible as
better **information efficiency** (for example fewer simulations and lower failure
density without reducing later-gate yield), not merely a single stronger Alpha.
