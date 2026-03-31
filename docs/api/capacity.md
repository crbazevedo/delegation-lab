# capacity

Operational feasibility and autonomy-limit tools. Answers: *"Can this pipeline hit the quality target at all?"*

*Paper reference: Section 1 (Delegation capacity, Theorem 1); Experiment 6*

## check_feasibility

::: minimal_oversight.capacity.check_feasibility
    options:
      show_source: false

The core decision function. Returns a `FeasibilityReport` with a human-readable verdict.

```python
from minimal_oversight.capacity import check_feasibility

report = check_feasibility(pipeline, p_min=0.80)
print(report.explanation)
# INFEASIBLE: Quality target p_min=0.800 exceeds pipeline
# capacity C_op=0.725. No governance policy can rescue this design.
```

## FeasibilityReport

| Field | Type | Description |
|-------|------|-------------|
| `feasible` | `bool` | $p_\text{min} \leq C_\text{op}$ |
| `c_op` | `float` | Pipeline quality ceiling |
| `p_min` | `float` | Quality target |
| `b_eff` | `float \| None` | Effective autonomy buffer (Eq. 16) |
| `h_crit` | `float \| None` | Critical process entropy |
| `bottleneck_node` | `str \| None` | The node limiting capacity |
| `explanation` | `str` | Human-readable verdict |

## Other functions

| Function | Returns | Description | Paper ref |
|----------|---------|-------------|-----------|
| `compute_node_capacity(node, η, δ)` | `float` | Single-node $C_\text{op}$ at fixed point | Eq. 10 |
| `compute_pipeline_capacity(pipeline, η, δ)` | `dict[str, float]` | Per-node capacity in topological order | Eq. 11 |
| `compute_c_op(pipeline)` | `float` | Pipeline ceiling (min over sinks) | Eq. 10 |
| `compute_buffer(c_op, p_min, λ, H)` | `float` | $B_\text{eff} = C_\text{op} - p_\text{min} - \lambda H(W)$ | Eq. 16 |

### compute_pipeline_capacity

Each node's effective skill depends on its parents' corrected quality (Eq. 7). The function walks the DAG in topological order, applying the recursive formula (Eq. 11) at each node.

```python
from minimal_oversight.capacity import compute_pipeline_capacity, compute_c_op

caps = compute_pipeline_capacity(pipeline)
for name, c_op in caps.items():
    print(f"{name}: C_op = {c_op:.3f}")

print(f"Pipeline ceiling: {compute_c_op(pipeline):.3f}")
```
