# minimal-oversight

[![CI](https://github.com/crbazevedo/delegation-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/crbazevedo/delegation-lab/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A governed-delegation analytics and decision-support toolkit.

Companion package to *"Minimal Oversight: A Theory of Principled Autonomy Delegation"* (Azevedo, 2026).

**[Documentation](https://crbazevedo.github.io/delegation-lab/)** | **[Paper](https://github.com/crbazevedo/delegation-lab)** | **[Notebooks](https://github.com/crbazevedo/delegation-lab/tree/main/notebooks)**

## What it does

Helps practitioners answer six questions about their multi-agent pipelines:

1. **Can this pipeline meet my target quality?** — feasibility check
2. **Where should I place review effort?** — water-filling allocation
3. **Which nodes are most dangerous?** — topology and masking analysis
4. **How much autonomy can I safely grant?** — autonomy buffer
5. **When should humans intervene?** — intervention scheduling
6. **What should stop being delegated?** — scope recommendations

## Quick start

```python
from minimal_oversight import analyze_pipeline
from minimal_oversight.models import Node, PipelineGraph, AggregationType

# Define your pipeline
gen = Node("generator", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50)
rev = Node("reviewer", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50)
merge = Node("merge", sigma_skill=0.55, catch_rate=0.65,
             aggregation=AggregationType.PRODUCT)

pipeline = PipelineGraph([gen, rev, merge])
pipeline.add_edge("generator", "reviewer")
pipeline.add_edge("reviewer", "merge")

# One call — full analysis
report = analyze_pipeline(pipeline, p_min=0.80)
print(report)
```

## Install

```bash
pip install -e ".[dev]"
```

## Package structure

| Module | Purpose |
|--------|---------|
| `models` | Node, PipelineGraph, GovernancePolicy, WorkflowTrace |
| `estimation` | Infer σ_raw, σ_corr, M*, catch rate, drift from logs |
| `capacity` | C_op, B_eff, feasibility checks, H_crit |
| `topology` | Motif detection, delegation centrality, fragility |
| `allocation` | AMO solver, scope selection, governance recommendations |
| `intervention` | T*_auto, intervention schedule, alerts, failure diagnosis |
| `viz` | Pipeline risk plots, masking dashboard, buffer view |
| `simulation` | Synthetic engine for what-if analysis (subordinate) |

## What it is not

- Not an agent framework
- Not a workflow orchestrator
- Not just a plotting library
- Not just the paper's reproduction code

It is a **governed-delegation analytics and decision-support library**.
