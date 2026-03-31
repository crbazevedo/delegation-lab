# Calibrating from Traces

The estimation module is the most useful part of the package in production. Given workflow traces, it infers the framework quantities that everything else operates on.

## What it estimates

| Quantity | How | What it tells you |
|----------|-----|-------------------|
| $\sigma_\text{raw}$ | Mean of pre-correction outcomes | Agent's actual competence |
| $\sigma_\text{corr}$ | Mean of post-correction outcomes | Delivered quality |
| $M^*$ | $\sigma_\text{corr} / \sigma_\text{raw}$ | How much the corrector is masking |
| $\hat{c}$ | $(\sigma_\text{corr} - \sigma_\text{raw}) / (1 - \sigma_\text{raw})$ | Corrector's catch rate |
| $H(W)$ | Entropy of routing path distribution | Workflow complexity |
| $\mu_\text{eff}$ | Slope of rolling $\sigma_\text{raw}$ | Drift rate |

## From generic event logs

Most flexible — map your field names to ours:

```python
from minimal_oversight.connectors.traces import from_generic_events, to_workflow_traces

events = [
    {"task_id": "t1", "node_id": "gen", "outcome": 1, "corrected": 1, "timestamp": 0},
    {"task_id": "t1", "node_id": "rev", "outcome": 0, "corrected": 1, "timestamp": 1},
    {"task_id": "t2", "node_id": "gen", "outcome": 1, "corrected": 1, "timestamp": 2},
]

norm = from_generic_events(
    events,
    task_id_field="task_id",
    node_id_field="node_id",
    outcome_field="outcome",
    corrected_field="corrected",     # optional: post-correction outcome
    reviewed_field=None,              # optional: was this item reviewed?
    timestamp_field="timestamp",
)
traces = to_workflow_traces(norm)
```

## The dual-σ requirement

The key insight: you need **both** pre-correction and post-correction outcomes to compute $M^*$. If your logs only have one, you get $\sigma_\text{corr}$ but not $\sigma_\text{raw}$, and you can't detect masking.

!!! tip "Implementation guide (from Box 3 in the paper)"
    At each delegation boundary, log **two** versions of every output:

    1. The raw output before any downstream correction
    2. The corrected output after review

    The storage cost is modest: only the diff or a quality score needs to be retained, not the full output.

## Bootstrap confidence intervals

```python
from minimal_oversight.estimation import estimate_node, bootstrap_ci

est = estimate_node("generator", traces, bootstrap=True)
print(f"σ_raw = {est.sigma_raw:.3f}")
print(f"95% CI: [{est.ci_sigma_raw[0]:.3f}, {est.ci_sigma_raw[1]:.3f}]")
```

## Sliding windows

For production monitoring, use a sliding window matched to the environment's rate of change:

```python
from minimal_oversight.estimation import estimate_sigma_raw

# Last 100 observations only
sigma = estimate_sigma_raw(outcomes, window=100)
```

The paper recommends setting the window to $1/\delta$ — the reciprocal of the decay rate — so the estimate reflects current competence, not stale history.
