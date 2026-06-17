# minimal-oversight

[![PyPI](https://img.shields.io/badge/PyPI-v0.1.3-blue.svg)](https://pypi.org/project/minimal-oversight/0.1.3/)
[![Release](https://img.shields.io/badge/release-v0.1.3-blue.svg)](https://github.com/crbazevedo/delegation-lab/releases/tag/v0.1.3)
[![CI](https://github.com/crbazevedo/delegation-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/crbazevedo/delegation-lab/actions/workflows/ci.yml)
[![Docs](https://github.com/crbazevedo/delegation-lab/actions/workflows/docs.yml/badge.svg)](https://github.com/crbazevedo/delegation-lab/actions/workflows/docs.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A governed-delegation analytics toolkit for delegated AI pipelines, centered on
the **Minimum Sufficient Oversight Principle (MSO)**.

Companion package to *"Minimal Oversight: Uncertainty-Aware Governance for Delegated AI Systems"* (Azevedo, 2026).

**[Documentation](https://crbazevedo.github.io/delegation-lab/)** | **[Interactive widgets](web/)** | **[Notebooks](https://github.com/crbazevedo/delegation-lab/tree/main/notebooks)** | **[Changelog](https://github.com/crbazevedo/delegation-lab/blob/main/CHANGELOG.md)**

Current release tag: [`v0.1.3`](https://github.com/crbazevedo/delegation-lab/releases/tag/v0.1.3) / PyPI package: [`minimal-oversight==0.1.3`](https://pypi.org/project/minimal-oversight/0.1.3/)

## What it does

Delegated AI systems route uncertain work through pipelines: one model proposes,
another reviews, a tool checks, and a gate decides what ships. The design
problem is no longer just accuracy; it is trust calibration under uncertainty:
how much autonomy to grant, where to place oversight, what quality ceiling the
system can sustain, and when intervention becomes necessary.

This package turns those questions into computable quantities:

| Question | What you get |
|----------|-------------|
| Can this pipeline meet my quality target? | Feasibility check: $C_\text{op}$ vs $p_\text{min}$ |
| Where should I place review effort? | Water-filling allocation via the Minimum Sufficient Oversight Principle |
| Which nodes are most dangerous? | Delegation centrality, masking index, SOTA score |
| How much autonomy can I safely grant? | Effective autonomy buffer $B_\text{eff}$ |
| When should humans intervene? | Autonomy time $T^*_\text{auto}$ and intervention schedule |
| What should stop being delegated? | Scope recommendations with coverage constraints |

In practical terms, MSO treats oversight as a constrained allocation problem:
meet a target quality level with the least sufficient review effort, then place
that effort where the model and pipeline state make review most informative.

## Interactive companion

A dependency-free, embeddable widget suite under [`web/`](web/) computes the
paper's quantities **live in the browser** — the same equations as this package.
Build or load a delegated workflow in the **governance cockpit** (connector
library, editable graph, merge gates, review loops, didactic lessons) and read
feasibility, masking, motifs, and risk off it; press **Run** to animate task
tokens through the graph. Focused explainers cover the masking pathology
(`M*=1.83`), water-filling allocation, the **Return Operator run on time**, a
**stochastic-Petri-net token simulation**, and a **water-filling-vs-baseline
benchmark**.

```bash
cd web && python -m http.server 8000   # then open http://localhost:8000
```

Grounding is mechanically enforced: `web/mso-core.js` is a faithful port of
`minimal_oversight._formulae` pinned to the package to within `1e-6`
(`tests/test_parity.py`), and the token simulator's empirical end-to-end success
is asserted to match the analytic `C_op` (`tests/test_sim_grounding.py`). See the
[Interactive Companion guide](https://crbazevedo.github.io/delegation-lab/guides/interactive/).

## Install

```bash
pip install minimal-oversight
```

For a reproducible install of the current release:

```bash
pip install minimal-oversight==0.1.3
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
| `allocation` | MSO solver, scope selection, governance recommendations |
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

It is a **governed-delegation analytics and decision-support library**, backed
by uncertainty-aware and information-theoretic foundations but presented through
practitioner questions and one-call analysis.

## Citation

```bibtex
@article{azevedo2026minimal,
  title={Minimal Oversight: Uncertainty-Aware Governance for Delegated AI Systems},
  author={Azevedo, Carlos R. B.},
  year={2026}
}
```
