# minimal-oversight

**Governed-delegation analytics and decision-support toolkit.**

Companion package to [*Minimal Oversight: A Theory of Principled Autonomy Delegation*](https://github.com/crbazevedo/delegation-lab) (Azevedo, 2026).

---

## What problem does this solve?

Multi-agent AI systems delegate work through pipelines: one model proposes, another reviews, a third tests, and a gate decides what ships. The design problem is no longer just accuracy — it's how much autonomy to grant, where to place oversight, what quality ceiling the system can sustain, and when intervention becomes necessary.

This package turns those questions into computable quantities.

## Six questions it answers

| Question | What you get |
|----------|-------------|
| Can this pipeline meet my quality target? | Feasibility check with `C_op` vs `p_min` |
| Where should I place review effort? | Water-filling allocation via the AMO |
| Which nodes are most dangerous? | Delegation centrality, masking index, SOTA score |
| How much autonomy can I safely grant? | Effective autonomy buffer `B_eff` |
| When should humans intervene? | Autonomy time `T*_auto` and intervention schedule |
| What should stop being delegated? | Scope recommendations with coverage constraints |

## One call

```python
from minimal_oversight import analyze_pipeline
from minimal_oversight.models import Node, PipelineGraph

# Define your pipeline
gen = Node("generator", sigma_skill=0.55, catch_rate=0.65)
rev = Node("reviewer", sigma_skill=0.55, catch_rate=0.65)
pipeline = PipelineGraph([gen, rev])
pipeline.add_edge("generator", "reviewer")

# Full analysis
report = analyze_pipeline(pipeline, p_min=0.80)
print(report)
```

Or import directly from your framework:

```python
# LangGraph
report = analyze_pipeline(compiled_graph, p_min=0.80)

# Google ADK
report = analyze_pipeline(adk_agent, p_min=0.80)
```

## What it is not

- Not an agent framework — it analyzes pipelines, not builds them
- Not a workflow orchestrator — it sits above LangGraph/ADK/CrewAI
- Not just a plotting library — visualizations serve the decision layer
- Not the paper's reproduction code — the [validation notebook](paper/validation.md) does that separately

It is a **governed-delegation analytics and decision-support library**, backed by rigorous information-theoretic foundations but presented through practitioner questions and one-call analysis.

## Architecture

```
┌─────────────────────────────────────────────┐
│         analyze_pipeline()                  │  ← Practitioner interface
├─────────────────────────────────────────────┤
│  estimation │ capacity │ topology │ viz     │  ← Decision modules
│  allocation │ intervention                  │
├─────────────────────────────────────────────┤
│  _formulae.py                               │  ← Paper equations (private)
├─────────────────────────────────────────────┤
│  schema.py │ connectors/                    │  ← Framework integration
│  langgraph │ adk │ traces                   │
└─────────────────────────────────────────────┘
```

Two layers: a rigorous core (`_formulae.py` — every numbered equation from the paper, tested) underneath a practitioner interface (typed reports, human-readable explanations, actionable recommendations). Practitioners never need to touch theorem notation.
