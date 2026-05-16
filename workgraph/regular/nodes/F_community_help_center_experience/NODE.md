# F Community / Help Center Experience

## Role

Collect platform/community experience relevant to the selected tower and E field pool.
This node is executed by a nodesubagent only.
Its first job is to connect the current run to the durable objective: high Value Factor / VF, higher weight, and Grand Master readiness.

## Required Inputs

- D `outputs/decision.json`, or BCD' `outputs/decision.json`.
- E `outputs/available_datafields.json`.
- If present, BCD' `outputs/seed_context.json` and `outputs/optimization_objective.json`.

## Required Outputs

- `outputs/community_queries.json`
- `outputs/community_evidence_raw.json`
- `outputs/community_experience.json`
- `outputs/gm_vf_weight_brief.json`
- Required common output bundle.

## Process Requirements

1. Search local community/help-center storage first, especially `wqb_core/dataset/forum/community.sqlite3` when available.
2. Use this query priority before any generic tower query:
   - Grand Master / Grandmaster / GM / Genius level / tie-breaker.
   - Value Factor / VF / high value factor / high VF.
   - weight factor / high weight / weight decreasing / payment multiplier.
   - Combined Alpha Performance / Combined Selected Alpha Performance / CAP / CSAP.
   - D tower, E datasets, E field families, and BCD' seed objective terms.
3. Rank evidence by signal, not just count:
   - exact title or body match beats loose comment match
   - high comment count and high vote comments are preferred
   - posts with concrete thresholds, workflow steps, or failure causes beat motivational replies
   - duplicate reposts across communities should be collapsed but referenced
4. Write `community_queries.json` with the exact query strings, source table, match count, rank rule, and reason for each query.
5. Write `community_evidence_raw.json` with source title, URL, table, topic/comment id, author when available, vote/comment count, matched terms, and short evidence excerpts.
6. Write `community_experience.json` as normalized findings grouped by:
   - `value_factor`
   - `weight`
   - `grand_master`
   - `combined_performance`
   - `tower_specific`
   - `field_specific`
7. Write `gm_vf_weight_brief.json` with direct implications for downstream nodes:
   - H mechanism constraints
   - I candidate generation constraints
   - J metrics and rejection gates
   - K diagnosis questions
8. Separate direct evidence from inference.
   Do not present community comments as platform rules unless the source is an official help-center article or clearly marked official post.
9. Record whether each source was fetched, cached, unavailable, or skipped.
10. Extract pitfalls, operator hints, and tower-specific cautions.
11. Do not select the next mechanism family.

## Current Forum Evidence To Preserve

The local forum snapshot has high-signal evidence that should shape this node's default reading path:

- High Value Factor posts repeatedly emphasize daily progress, avoiding overfit, low self/production correlation, turnover awareness, automation for quantity, and not optimizing Sharpe alone.
- CAP/CSAP posts warn that high VF can diverge from combined performance; downstream candidates should be diverse, orthogonal, portfolio-compatible, and cost-aware.
- Weight discussions point back to alpha quality, uniqueness, signal-to-noise, decay, low correlation, cross-region/style diversity, and consistent submission rather than only more submissions.
- GM journey posts emphasize combine thresholds, pyramid coverage, field/operator-per-alpha tie-breakers, margin, turnover, template quality, correlation pruning, and prefiltering missing or weak fields before large simulation batches.
- Several Chinese GM/VF posts frame practical targets such as many distinct pyramids, controlled field/operator usage, margin above trivial levels, and avoiding low-margin alphas that cannot cover costs.

## Success Criteria

- H can read structured community evidence.
- H/I/J can see how high-VF, high-weight, and GM goals constrain mechanism choice, candidate breadth, metrics, and rejection gates.
- Missing optional community evidence is marked `degraded`, not silently omitted.

## Block Conditions

- D/BCD' or E outputs are missing.
- No usable query can be formed.
