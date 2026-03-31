# Reading the Report

A guide to interpreting `analyze_pipeline()` output and acting on it.

## The quick version

If you read nothing else, check three things:

1. **Is it feasible?** `report.feasibility.feasible` — if `False`, stop. Redesign first.
2. **Where's the masking?** `report.alerts` — any `CRITICAL` masking alerts need attention now.
3. **What to change first?** `report.recommendations[0]` — the highest-priority action.

## Feasibility

```python
f = report.feasibility
```

| Field | Meaning |
|-------|---------|
| `f.feasible` | `True` if $p_\text{min} \leq C_\text{op}$ |
| `f.c_op` | Pipeline's quality ceiling |
| `f.p_min` | Your quality target |
| `f.b_eff` | Autonomy buffer (positive = safe, zero = cliff, negative = impossible) |
| `f.bottleneck_node` | The node that limits capacity |
| `f.explanation` | Human-readable verdict |

**If infeasible:** No routing rule, review allocation, or monitoring strategy will help. You need better agents, better correctors, or a different topology.

**If feasible but `b_eff` is small (< 0.05):** The pipeline is near the autonomy cliff. Any increase in workflow complexity or drift could push it over. Simplify routing or increase review capacity.

## Alerts

```python
for alert in report.alerts:
    print(f"[{alert.level.value}] {alert.node_name}: {alert.message}")
```

Three categories:

| Alert | Trigger | Action |
|-------|---------|--------|
| Masking ($M^* > \tau$) | Corrector hiding weakness | Track $\sigma_\text{raw}$ separately |
| Buffer ($B_\text{eff} < 0.05$) | Near autonomy cliff | Simplify or increase review |
| Capacity ($K/N < \text{threshold}$) | Corrector overloaded | Increase review capacity or reduce scope |

## Recommendations

```python
for r in report.recommendations:
    print(f"{r.priority}. [{r.target_node}] {r.action}")
    print(f"   Why: {r.rationale}")
    print(f"   Impact: {r.expected_impact}")
```

Recommendations are sorted by the SOTA priority score: $S(v) = \text{DC}(v) \times M^*(v) \times \kappa(v)$. The node where governance investment produces the largest improvement appears first.

## Intervention schedule

```python
for s in report.intervention_schedule:
    print(f"{s.node_name}: review every {s.t_auto:.0f} steps")
```

Nodes with short $T^*_\text{auto}$ need frequent human review. Nodes with long $T^*_\text{auto}$ can operate autonomously. The schedule is a linear program that minimizes total review cost subject to meeting each node's minimum frequency.

## If you observe...

| Observation | Diagnosis | Paper reference |
|-------------|-----------|-----------------|
| High $\sigma_\text{corr}$ but falling $\sigma_\text{raw}$ | Masking deterioration | Table 9, row 1 |
| $p_\text{min} > C_\text{op}$ | Infeasible — redesign | Table 9, row 2 |
| Large $\lambda H(W)$ eating the buffer | Process overload | Table 9, row 3 |
| One node with very short $T^*_\text{auto}$ | Operational bottleneck | Table 9, row 4 |
| Quality drops only when upstream A fails | Diamond fragility | Table 9, row 5 |
| Scope collapses to easy tasks only | Missing coverage constraint | Table 9, row 6 |
