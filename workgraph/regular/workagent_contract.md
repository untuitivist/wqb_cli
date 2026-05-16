# Workagent Contract

Use this contract when coordinating a WQB research workgraph run.

## Startup

1. Create a run directory with `workgraph/regular/scripts/init_run.py`.
2. Use only the returned `research_runs/run_YYYYMMDD_HHMMSS/` directory for runtime writes.
3. Read `workgraph/regular/node_registry.json`.
4. Keep all graph decisions in `graph_state.json`.

## Scheduling Rules

- Schedule only nodes whose `required_upstream` nodes have completed with `success` or accepted `degraded`.
- Do not schedule D until B and C have completed.
- Do not schedule E/F/G/H without a D output.
- If the user provides `alpha_id` and `optimization_objective`, schedule `BCD_prime_seed_alpha_objective` after A instead of B/C/D.
- Treat `BCD_prime_seed_alpha_objective.outputs/decision.json` as D-equivalent for E/F/G/H.
- Do not schedule both the B/C/D discovery path and `BCD_prime_seed_alpha_objective` in the same linear branch.
- Do not schedule I when E has an empty candidate field pool.
- Do not schedule M in live mode unless the user explicitly asks for live submission.
- Do not execute node work directly as the workagent.
- Do not call WQB APIs, build datasets, generate expressions, run simulations, or diagnose alphas directly as the workagent.
- Use a nodesubagent for every node execution, including simple inspection nodes.

## Nodesubagent Task Envelope

Give a nodesubagent only:

- active run directory
- assigned node directory
- node id and node contract
- paths to required upstream artifacts inside the active run directory
- explicit write boundary: assigned node directory only

Never ask a nodesubagent to decide the graph branch.
Require the nodesubagent to write the full output bundle defined in `workgraph/regular/node_output_contract.md`.
Reject a node result if `process_log.md`, `evidence_index.json`, `handoff.md`, or `node_result.json` is missing.

## Completion

After a node finishes:

1. Run `workgraph/regular/scripts/validate_run_scope.py <run_dir>`.
2. Inspect `node_result.json`.
3. Update `graph_state.json` with `workgraph/regular/scripts/update_graph_state.py`.
4. Decide the next node from `allowed_next`.

If validation reports run-external writes, stop immediately.
If a node output is thin or missing evidence, mark the node as blocked and ask a new nodesubagent to redo the same node inside a new node directory.
