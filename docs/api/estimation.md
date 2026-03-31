# estimation

The most useful module in production. Given workflow traces, it infers the framework quantities that everything else operates on.

*Paper reference: Section 1 (signal definitions); Section 4 (Table 5, identifiability)*

## estimate_node

::: minimal_oversight.estimation.estimate_node
    options:
      show_source: false

The workhorse function — estimates all quantities for a single node from traces.

```python
from minimal_oversight.estimation import estimate_node

est = estimate_node("reviewer", traces, window=100, bootstrap=True)
print(f"σ_raw = {est.sigma_raw:.3f}")
print(f"σ_corr = {est.sigma_corr:.3f}")
print(f"M* = {est.masking_index:.2f}")
print(f"ĉ = {est.catch_rate:.2f}")
print(f"95% CI: [{est.ci_sigma_raw[0]:.3f}, {est.ci_sigma_raw[1]:.3f}]")
```

## EstimationResult

| Field | Type | Description |
|-------|------|-------------|
| `node_name` | `str` | Which node this estimate is for |
| `sigma_raw` | `float` | Estimated raw competence |
| `sigma_corr` | `float` | Estimated corrected quality |
| `masking_index` | `float` | $M^* = \sigma_\text{corr} / \sigma_\text{raw}$ |
| `catch_rate` | `float \| None` | Inferred corrector catch rate |
| `sample_size` | `int` | Number of observations |
| `ci_sigma_raw` | `tuple \| None` | 95% bootstrap CI for $\sigma_\text{raw}$ |
| `ci_sigma_corr` | `tuple \| None` | 95% bootstrap CI for $\sigma_\text{corr}$ |

## Individual estimators

| Function | Input | Output | Paper ref |
|----------|-------|--------|-----------|
| `estimate_sigma_raw(outcomes, window)` | Binary outcomes | $\sigma_\text{raw}$ | Eq. 5 |
| `estimate_sigma_corr(outcomes, window)` | Corrected outcomes | $\sigma_\text{corr}$ | Eq. 6 |
| `estimate_masking_index(σ_corr, σ_raw)` | Two floats | $M^*$ | §1 |
| `estimate_catch_rate(raw, corrected)` | Paired outcomes | $\hat{c}$ | Inferred |
| `estimate_process_entropy(traces, pipeline)` | Traces + graph | $H(W)$ bits | Eq. 14 |
| `estimate_drift(outcomes, window_size, step)` | Outcome sequence | $\mu_\text{eff}$ | §4 |
| `estimate_noise(outcomes, window_size, step)` | Outcome sequence | $\nu_\text{eff}^2$ | §4 |
| `bootstrap_ci(outcomes, n_resamples, confidence)` | Outcomes | (lo, hi) | §3 |

### Catch rate

Inferred as $\hat{c} = (\sigma_\text{corr} - \sigma_\text{raw}) / (1 - \sigma_\text{raw})$. Returns `None` if $\sigma_\text{raw} \approx 1$ (no errors to catch).

### Process entropy

Simplified v1: counts unique routing paths and computes Shannon entropy. The paper defines $H(W) = H(\text{routing}) + H(\text{tools}) + H(\text{timing})$ (Eq. 14); the current implementation captures the routing term.

### Drift and noise

Fit from rolling windows. Drift ($\mu_\text{eff}$) is the negative linear trend slope; noise ($\nu_\text{eff}^2$) is the mean rolling variance. Set `window_size` to $1/\delta$ for estimates that reflect current competence.
