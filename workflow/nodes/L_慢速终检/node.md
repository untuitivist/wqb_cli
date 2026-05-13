# L_Slow_Final_Check

## Role
- Run a slower final gate after `K` when at least one alpha looks submit-worthy.
- Decide whether the workflow can move to `M`, or should fall back from `L`.

## Upstream
- `K_结果诊断`

## Downstream
- `M_提交_点塔_进池_SA_OSM`
- `E_数据与字段可行性`
- `D_选主塔`

## Inputs
### Necessary
- Latest `*_node_K_diagnosis/diagnosis__{REGION}_D{DELAY}_{CATEGORY}.json`
- Real `alpha_id` values selected from `K`
- `wqb_core.simulation.check.py`
- `wqb_core.alpha.get_submission_check.py`
- `wqb_core.alpha.get_correlation.py`

### Optional
- Historical comparison notes from earlier `L`
- Additional metadata to attach before submission

## Outputs
### Necessary
- `*_node_L_slow_final_check/slow_final_check__{REGION}_D{DELAY}_{CATEGORY}.json`
- `*_node_L_slow_final_check/submission_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- `*_node_L_slow_final_check/node_summary.md`

### Optional
- Detailed per-alpha raw check payloads
- Fallback recommendation from `L` back to `E` or `D`

## Success Criteria
- Every chosen alpha has a slow-check record or an explicit fetch failure.
- `L` emits an explicit next decision:
  - move to `M`
  - fall back to `E`
  - fall back to `D`

## Failure Criteria
- No real `alpha_id` can be evaluated.
- `L` cannot determine whether submission should continue.
