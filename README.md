# minimal-oversight

[![PyPI](https://img.shields.io/pypi/v/minimal-oversight.svg)](https://pypi.org/project/minimal-oversight/)
[![CI](https://github.com/crbazevedo/delegation-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/crbazevedo/delegation-lab/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A governed-delegation analytics and decision-support toolkit.

Companion package to *"Minimal Oversight: A Theory of Principled Autonomy Delegation"* (Azevedo, 2026).

**[Documentation](https://crbazevedo.github.io/delegation-lab/)** | **[Notebooks](https://github.com/crbazevedo/delegation-lab/tree/main/notebooks)** | **[Changelog](https://github.com/crbazevedo/delegation-lab/blob/main/CHANGELOG.md)**

## What it does

Multi-agent AI systems delegate work through pipelines: one model proposes, another reviews, a third tests, and a gate decides what ships. The design problem is no longer just accuracy — it's how much autonomy to grant, where to place oversight, and when intervention becomes necessary.

This package turns those questions into computable quantities:

| Question | What you get |
|----------|-------------|
| Can this pipeline meet my quality target? | Feasibility check: $C_\text{op}$ vs $p_\text{min}$ |
| Where should I place review effort? | Water-filling allocation via the AMO |
| Which nodes are most dangerous? | Delegation centrality, masking index, SOTA score |
| How much autonomy can I safely grant? | Effective autonomy buffer $B_\text{eff}$ |
| When should humans intervene? | Autonomy time $T^*_\text{auto}$ and intervention schedule |
| What should stop being delegated? | Scope recommendations with coverage constraints |

## Install

```bash
pip install minimal-oversight
```

With framework connectors and visualization:

```bash
pip install minimal-oversight[frameworks,viz]
```

## Quick start

### From scratch

```python
from minimal_oversight import analyze_pipeline
from minimal_oversight.models import Node, PipelineGraph, AggregationType

gen = Node("generator", sigma_skill=0.55, catch_rate=0.65)
rev = Node("reviewer",  sigma_skill=0.60, catch_rate=0.70)
merge = Node("merge",   sigma_skill=0.55, aggregation=AggregationType.PRODUCT)

pipeline = PipelineGraph([gen, rev, merge])
pipeline.add_edge("generator", "reviewer")
pipeline.add_edge("reviewer", "merge")

report = analyze_pipeline(pipeline, p_min=0.80)
print(report)
```

### From LangGraph

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(MyState)
graph.add_node("researcher", research_fn)
graph.add_node("writer", write_fn)
graph.add_edge("researcher", "writer")
graph.add_edge("writer", END)
graph.set_entry_point("researcher")

report = analyze_pipeline(graph.compile(), p_min=0.80)
```

### From Google ADK

```python
from google.adk import Agent

root = Agent(name="support", model="gemini-2.0-flash", sub_agents=[
    Agent(name="billing", model="gemini-2.0-flash"),
    Agent(name="tech",    model="gemini-2.0-flash"),
])

report = analyze_pipeline(root, p_min=0.80)
```

### From production logs

```python
from minimal_oversight.connectors.traces import from_generic_events, to_workflow_traces

events = [
    {"task_id": "t1", "node_id": "gen", "outcome": 1, "corrected": 1, "timestamp": 0},
    {"task_id": "t1", "node_id": "rev", "outcome": 0, "corrected": 1, "timestamp": 1},
]
traces = to_workflow_traces(from_generic_events(events, corrected_field="corrected"))
report = analyze_pipeline(pipeline, p_min=0.80, traces=traces)
```

## Architecture

```
                     analyze_pipeline()              Practitioner interface
              ┌──────────────────────────────┐
              │  estimation  capacity        │
              │  topology    allocation      │       Decision modules
              │  intervention  viz           │
              ├──────────────────────────────┤
              │  _formulae.py                │       Paper equations (private)
              ├──────────────────────────────┤
              │  schema   connectors/        │
              │  langgraph  adk  traces      │       Framework integration
              └──────────────────────────────┘
```

## Modules

| Module | Purpose |
|--------|---------|
| `models` | Node, PipelineGraph, GovernancePolicy, WorkflowTrace |
| `estimation` | Infer $\sigma_\text{raw}$, $\sigma_\text{corr}$, $M^*$, catch rate, drift from logs |
| `capacity` | $C_\text{op}$, $B_\text{eff}$, feasibility checks, $H_\text{crit}$ |
| `topology` | Motif detection, delegation centrality, conditional fragility |
| `allocation` | AMO solver, scope selection, governance recommendations |
| `intervention` | $T^*_\text{auto}$, intervention schedule, alerts, failure diagnosis |
| `viz` | Masking dashboard, autonomy buffer, risk ranking, scope frontier |
| `connectors` | LangGraph, Google ADK, LangSmith, generic trace parsers |

## Notebooks

| # | Topic | Shows |
|---|-------|-------|
| 01 | [SDLC pipeline](notebooks/01_sdlc_pipeline.ipynb) | Fan-out/merge, SOTA placement, masking |
| 02 | [Customer support](notebooks/02_customer_support.ipynb) | Chain depth, drift, diagnostic differential |
| 03 | [Topology stress test](notebooks/03_topology_stress_test.ipynb) | All 4 motifs compared |
| 04 | [LangGraph import](notebooks/04_langgraph_import.ipynb) | Real StateGraph + conditional edges |
| 05 | [ADK import](notebooks/05_adk_import.ipynb) | Real Agent objects + session logs |
| 06 | [Paper validation](notebooks/06_paper_validation.ipynb) | All 8 experiments from Section 3 |

## What it is not

- Not an agent framework — it analyzes pipelines, not builds them
- Not a workflow orchestrator — it sits above LangGraph / ADK / CrewAI
- Not just the paper's reproduction code — that's [one notebook](notebooks/06_paper_validation.ipynb)

It is a **governed-delegation analytics and decision-support library**, backed by information-theoretic foundations but presented through practitioner questions and one-call analysis.

## Citation

```bibtex
@article{azevedo2026minimal,
  title={Minimal Oversight: A Theory of Principled Autonomy Delegation},
  author={Azevedo, Carlos R. B.},
  year={2026}
}
```
