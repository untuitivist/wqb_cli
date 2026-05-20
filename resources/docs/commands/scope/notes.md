# scope Notes

`wqb scope` is a local inspection layer over `data_all`.
It does not call `api.worldquantbrain.com`.

The command defaults to `info_data.bin` because loading `all_data.pickle` is expensive.
The large pickle contains, for each `REGION_DELAY`, four dataframes:

- base alpha metadata: `id`, `datafield`, `dataset`, `category`, classifications, operator count.
- simulation settings.
- IS metrics.
- OS metrics.

The quick index stores aggregate ratios by `datafield`, `dataset`, `category`, and neutralization.
These ratios are historical screening signals, not a guarantee that a new alpha will pass.

`pickle-summary` and `alpha-rows` intentionally load the full pickle.
Use them after quick-index screening to inspect real alpha ids, field combinations, settings, IS metrics, and OS metrics.
`alpha-rows` filters by exact `datafield` or `dataset` using the base table, then applies the matching ids to `base`, `settings`, `is`, or `os`.
