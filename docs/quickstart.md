# Quick Start

## Install

```bash
pip install minimal-oversight
```

With framework connectors:

```bash
pip install minimal-oversight[frameworks]  # adds langgraph + google-adk
```

With visualization:

```bash
pip install minimal-oversight[viz]  # adds matplotlib + plotly
```

## Your first analysis in 30 seconds

```python
from minimal_oversight import analyze_pipeline
from minimal_oversight.models import Node, PipelineGraph, AggregationType

# A simple 3-node pipeline: generate → review → merge
gen = Node("generator", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50)
rev = Node("reviewer",  sigma_skill=0.60, catch_rate=0.70, review_capacity=0.60)
merge = Node("merge",   sigma_skill=0.55, catch_rate=0.65,
             aggregation=AggregationType.PRODUCT)

pipeline = PipelineGraph([gen, rev, merge])
pipeline.add_edge("generator", "reviewer")
pipeline.add_edge("reviewer", "merge")

report = analyze_pipeline(pipeline, p_min=0.80)
print(report)
```

The report tells you:

- **Feasibility**: can this pipeline hit 80% quality?
- **Per-node masking**: where is the corrector hiding weakness?
- **Bottleneck**: which node limits the system?
- **Intervention schedule**: how often does each node need review?
- **Recommendations**: what to change first, and why

## From a LangGraph workflow

```python
from langgraph.graph import StateGraph, END
from minimal_oversight import analyze_pipeline

# Your existing workflow
graph = StateGraph(MyState)
graph.add_node("researcher", research_fn)
graph.add_node("writer", write_fn)
graph.add_edge("researcher", "writer")
graph.add_edge("writer", END)
graph.set_entry_point("researcher")
compiled = graph.compile()

# One call — auto-detected
report = analyze_pipeline(compiled, p_min=0.80)
print(report)
```

## From a Google ADK agent

```python
from google.adk import Agent
from minimal_oversight import analyze_pipeline

root = Agent(
    name="support",
    model="gemini-2.0-flash",
    sub_agents=[
        Agent(name="billing", model="gemini-2.0-flash"),
        Agent(name="tech", model="gemini-2.0-flash"),
    ],
)

report = analyze_pipeline(root, p_min=0.80)
print(report)
```

## From production logs

```python
from minimal_oversight.connectors.traces import from_generic_events, to_workflow_traces

# Your log format
events = [
    {"task_id": "t1", "node_id": "gen", "outcome": 1, "corrected": 1, "timestamp": 0},
    {"task_id": "t1", "node_id": "rev", "outcome": 0, "corrected": 1, "timestamp": 1},
    # ...
]

traces = to_workflow_traces(from_generic_events(
    events, corrected_field="corrected"
))
report = analyze_pipeline(pipeline, p_min=0.80, traces=traces)
```

## Next steps

- [Concepts](concepts/delegation.md) — understand the theory in plain language
- [Guides](guides/analyze.md) — detailed usage for each module
- [Paper validation](paper/validation.md) — the 8 experiments reproduced
- [API reference](api/models.md) — every class and function
