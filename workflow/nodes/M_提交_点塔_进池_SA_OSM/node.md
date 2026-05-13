# M_Submit_Light_Tower_Pool_SA_OSM

## Role
- Materialize the final submission step after `L`.
- Keep a safe review mode and an explicit execute mode.

## Upstream
- `L_慢速终检`

## Downstream
- workflow end for this tower branch

## Inputs
### Necessary
- Latest `*_node_L_slow_final_check/submission_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- Real `alpha_id` values approved by `L`
- `wqb_core.simulation.submit.py`

### Optional
- `wqb_core.alpha.set_alpha_properties.py`
- Alpha metadata such as tags or descriptions
- Explicit execution mode

## Outputs
### Necessary
- `*_node_M_submit_light_tower_pool_sa_osm/submission_actions__{REGION}_D{DELAY}_{CATEGORY}.json`
- `*_node_M_submit_light_tower_pool_sa_osm/submit_results__{REGION}_D{DELAY}_{CATEGORY}.json`
- `*_node_M_submit_light_tower_pool_sa_osm/node_summary.md`

### Optional
- Per-alpha property patch response
- Submit response payloads

## Success Criteria
- The final action plan is explicit.
- In review mode, the node produces a complete no-op preview.
- In execute mode, every approved alpha records a submit result or explicit failure.

## Failure Criteria
- Approved candidates from `L` cannot be loaded.
- Execute mode runs without a result record.
