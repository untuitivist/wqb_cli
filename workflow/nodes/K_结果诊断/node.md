# K_Diagnosis

## Role
- Diagnose real `alpha_id` results from `J`.
- Decide whether the workflow should go to `L`, roll back to `D/E/H/I`, or trigger `BEST_K_BRANCH`.

## Upstream
- `J_并行回测`

## Downstream
- `L_慢速终检`
- `D_选主塔`
- `E_数据与字段可行性`
- `H_经济学机制假设`
- `I_表达式候选集`
- `BEST_K_BRANCH`

## Inputs
### Necessary
- Latest `*_node_J_parallel_simulation/alpha_candidates__{REGION}_D{DELAY}_{CATEGORY}.json`
- Alpha details fetched via `wqb_core.alpha.get_alpha_details.py`

### Optional
- Visualization-enabled simulation details
- Additional PnL or deeper recordset pulls
- Historical `K` diagnosis files in the same run for best-branch comparison

## Outputs
### Necessary
- `*_node_K_diagnosis/alpha_details__{REGION}_D{DELAY}_{CATEGORY}.json`
- `*_node_K_diagnosis/diagnosis__{REGION}_D{DELAY}_{CATEGORY}.json`
- `*_node_K_diagnosis/survivors__{REGION}_D{DELAY}_{CATEGORY}.json`
- `*_node_K_diagnosis/node_summary.md`

### Optional
- `best_historical_k` comparison block inside diagnosis
- `<best_K_dir>/error_branch/...` archive when `BEST_K_BRANCH` is triggered

## Success Criteria
- Every `alpha_id` has a detail record or an explicit fetch failure record.
- A ranked diagnosis list is produced.
- The next decision is explicit:
  - go to `L`
  - roll back to `D/E/H/I`
  - or trigger `BEST_K_BRANCH`

## Failure Criteria
- Only simulation ids are available without real alpha diagnosis.
- No next-node decision can be made.
