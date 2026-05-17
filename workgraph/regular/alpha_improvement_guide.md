# Alpha Improvement Guide

This guide captures platform tutorial knowledge that nodes should use when improving REGULAR alphas.
It is an operational reference for H, I, K, and L.

## Operator Families

### Cross-sectional operators

Use cross-sectional operators when the alpha needs to compare instruments on the same date.

- `rank(x)` maps an input vector across instruments to a roughly uniform 0 to 1 distribution.
- Ranking can reduce extreme concentration from raw ratios such as `sales / assets`.
- Ranking is often useful when raw values create excessive weights or unstable scaling.

Typical use:

```text
rank(sales / assets)
```

### Time-series operators

Use time-series operators when the signal depends on each instrument's own history.

- `ts_rank(x, d)` ranks the current value of `x` against the past `d` days for the same instrument.
- `ts_delta(x, d)` returns the difference between today's `x` and the value `d` days ago.

Typical uses:

```text
ts_rank(sales / assets, 60)
-ts_delta(close, 2)
```

### Ratio and divide patterns

Ratios such as `close / open`, `sales / assets`, or field-to-field normalizations can create useful relative signals.
They also create risks:

- denominator near zero
- incompatible units
- extreme values
- high production correlation if the ratio is a common template

K should identify these risks.
I should prefer rank, winsorization, zscore, ts_rank, or guarded transforms when raw ratios are too linear or too concentrated.

## Settings Improvement

Use settings as a controlled improvement surface, not random tuning.

### Region and Universe

- `region` defines the market being simulated.
- `universe` defines the tradable stock pool, such as `TOP3000`.
- Larger universes can help sub-universe checks in some cases, but may change field coverage and noise.

### Decay

Decay averages alpha signal over time.
It can reduce turnover, but too much decay weakens the signal.

Use decay changes when:

- turnover is too high
- PnL is too noisy
- signal is plausible but unstable day to day

Avoid large decay jumps unless K shows turnover or PnL instability is the dominant failure.

### Truncation

Truncation limits maximum single-stock position weight.
Recommended exploration is usually around `0.05` to `0.10`.

Use truncation changes when:

- weight concentration appears
- raw signal has extreme outliers
- a few instruments dominate PnL or exposure

### Neutralization

Neutralization removes broad market or group exposure from alpha values.
Common choices include `Market`, `Industry`, and `Subindustry`.

Use neutralization changes when:

- market or industry exposure dominates the result
- correlation is high because the alpha is mostly a broad factor
- sub-universe or concentration warnings suggest poor diversification

Do not use neutralization as a substitute for a weak mechanism.
If the mechanism disappears after reasonable neutralization, branch back to H.

## Diagnosis to Action Map

K should translate result problems into concrete graph branches:

- Low Sharpe: improve mechanism in H, reduce noise with ts operators in I, or adjust decay if the signal is unstable but plausible.
- Low Fitness: increase Sharpe/Returns or reduce excessive turnover.
- Turnover too high: try decay, ts smoothing, slower windows, or less reactive operators.
- Turnover too low: reduce decay/window length or use a more responsive operator.
- High prod_corr: change field family in E, mechanism in H, or transform in I with rank/ts_rank/nonlinear compression.
- High self_corr: diversify expression structure, field family, or settings; avoid minor parameter-only variants.
- Low margin: reduce churn, improve selectivity, and avoid weak high-turnover signals.
- High drawdown or unstable PnL shape: prefer mechanism revision over parameter tuning.
- Weight concentration: use rank, truncation, neutralization, winsorization, or broader field construction.
- Unit warning: inspect expression construction; fix in I unless platform explicitly marks it harmless.
- Sub-universe Sharpe failure: consider universe choice, field breadth, concentration, and mechanism robustness.

