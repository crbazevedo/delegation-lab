# Analyzing a Pipeline

`analyze_pipeline()` is the package's flagship API. One call, full report.

## Inputs

```python
from minimal_oversight import analyze_pipeline

report = analyze_pipeline(
    pipeline,                   # PipelineGraph, LangGraph, ADK Agent, or dict
    p_min=0.80,                 # quality target
    traces=workflow_traces,     # optional: calibrate from logs
    governance_gap=0.02,        # λ — complexity sensitivity (~0.02/bit)
    process_entropy=0.0,        # H(W) — estimated from routing traces
    eta=10.0,                   # observation rate
    delta=2.0,                  # decay rate
)
```

## What's in the report

The `PipelineReport` contains:

| Section | What it tells you |
|---------|-------------------|
| `report.feasibility` | Can the pipeline hit `p_min`? `C_op`, `B_eff`, bottleneck node |
| `report.node_estimates` | Per-node `σ_raw`, `σ_corr`, `M*`, catch rate (from traces) |
| `report.node_capacities` | Per-node capacity from theory |
| `report.motifs` | Detected topology patterns (chain, fan-out, diamond, merge) |
| `report.node_risks` | Nodes ranked by delegation centrality and SOTA score |
| `report.intervention_schedule` | Per-node `T*_auto` and review frequency |
| `report.alerts` | Masking warnings, buffer alerts, capacity threshold breaches |
| `report.recommendations` | Ordered list of actionable governance changes |
| `report.failure_explanation` | Human-readable failure surface analysis |

## Reading the output

```python
print(report)  # formatted summary

# Or access sections directly
if not report.feasibility.feasible:
    print(f"Target {report.feasibility.p_min} exceeds capacity {report.feasibility.c_op}")
    print(f"Bottleneck: {report.feasibility.bottleneck_node}")

for r in report.recommendations[:3]:
    print(f"{r.priority}. [{r.target_node}] {r.action}")
    print(f"   {r.rationale}")
```

## With and without traces

**Without traces:** Parameters come from `Node` attributes or role-based defaults. Good for design-time analysis ("can this architecture work?").

**With traces:** `estimation.py` computes `σ_raw`, `σ_corr`, `M*`, and catch rate from real outcomes. The report includes confidence intervals. This is production monitoring.

```python
# Design time — use estimated parameters
report = analyze_pipeline(pipeline, p_min=0.80)

# Production — use real logs
report = analyze_pipeline(pipeline, p_min=0.80, traces=production_traces)
```
