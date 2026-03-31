# viz

Visualization helpers. Most practitioners will understand the framework through these.

**Requires:** `pip install minimal-oversight[viz]`

## plot_masking_dashboard

::: minimal_oversight.viz.plot_masking_dashboard
    options:
      show_source: false

Side-by-side view: $\sigma_\text{raw}$ vs $\sigma_\text{corr}$ (left) and $M^*$ per node (right). Nodes above the masking threshold are highlighted in red.

```python
from minimal_oversight.viz import plot_masking_dashboard

fig = plot_masking_dashboard(
    node_names=["gen", "rev", "test", "merge"],
    sigma_raw=[0.46, 0.38, 0.33, 0.13],
    sigma_corr=[0.69, 0.60, 0.56, 0.42],
    masking_threshold=1.3,
)
```

## plot_autonomy_buffer

::: minimal_oversight.viz.plot_autonomy_buffer
    options:
      show_source: false

Shows $B_\text{eff}$ as a function of process entropy $H(W)$, with the capacity cliff at $H_\text{crit}$ marked. Blue region = feasible; red region = infeasible.

```python
from minimal_oversight.viz import plot_autonomy_buffer

fig = plot_autonomy_buffer(c_op=0.86, p_min=0.75, governance_gap=0.02)
```

## plot_pipeline_risk

::: minimal_oversight.viz.plot_pipeline_risk
    options:
      show_source: false

Horizontal bar chart ranking nodes by SOTA priority score $S(v)$, annotated with $M^*$. Colors: red ($M^* > 1.5$), orange ($> 1.2$), green (healthy).

```python
from minimal_oversight.viz import plot_pipeline_risk

fig = plot_pipeline_risk(
    node_names=["rev", "gen", "test", "merge"],
    sota_scores=[1.32, 0.45, 0.62, 0.79],
    masking_indices=[1.77, 1.35, 1.49, 1.65],
)
```

## plot_scope_frontier

::: minimal_oversight.viz.plot_scope_frontier
    options:
      show_source: false

Coverage-cost frontier: how total governance cost increases (blue, left axis) and average delegated competence decreases (red, right axis) as coverage requirements tighten. Demonstrates why coverage constraints are not decorative — they prevent cherry-picking easy tasks.

```python
from minimal_oversight.viz import plot_scope_frontier
import numpy as np

fig = plot_scope_frontier(
    sigma_raw=np.random.default_rng(42).beta(3, 2, size=50),
    p_min=0.30,
)
```
