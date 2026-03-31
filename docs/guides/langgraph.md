# LangGraph Integration

Import a LangGraph `StateGraph` or `CompiledStateGraph` directly.

## Basic usage

```python
from langgraph.graph import StateGraph, END
from minimal_oversight import analyze_pipeline

graph = StateGraph(MyState)
graph.add_node("researcher", research_fn)
graph.add_node("writer", write_fn)
graph.add_node("reviewer", review_fn)
graph.add_edge("researcher", "writer")
graph.add_edge("writer", "reviewer")
graph.add_edge("reviewer", END)
graph.set_entry_point("researcher")

compiled = graph.compile()

# Auto-detected — just pass the compiled graph
report = analyze_pipeline(compiled, p_min=0.80)
```

## What the connector extracts

- **Nodes:** from `compiled.builder.nodes` — skips `__start__` and `__end__`
- **Edges:** from `compiled.builder.edges` — regular edges
- **Conditional edges:** from `compiled.builder.branches` — fan-out routing
- **Descriptions:** from function docstrings (via `StateNodeSpec.runnable.func.__doc__`)
- **Roles:** inferred from node names and descriptions (generator, reviewer, router, etc.)

## Explicit import with overrides

```python
from minimal_oversight.connectors.langgraph import from_langgraph

pipeline = from_langgraph(compiled, parameter_overrides={
    "researcher": {"sigma_skill": 0.80},  # you know this one is strong
    "writer": {"sigma_skill": 0.45},       # and this one struggles
})
```

## Conditional edges

`add_conditional_edges()` creates fan-out patterns that the framework detects:

```python
graph.add_conditional_edges(
    "classifier",
    routing_fn,
    {"simple": "handler_a", "complex": "handler_b"},
)
```

The connector extracts both targets from the `BranchSpec` and creates proper edges. Motif detection will flag this as a fan-out with the classifier as a high-centrality node.

## Calibrating from LangSmith

```python
from langsmith import Client
from minimal_oversight.connectors.traces import from_langsmith_traces, to_workflow_traces

client = Client()
runs = client.list_runs(project_name="my-project", run_type="chain", is_root=True)

# Convert to dicts for the parser
run_dicts = [{"id": str(r.id), "name": r.name, "run_type": r.run_type,
              "status": r.status, "error": r.error,
              "start_time": r.start_time.isoformat(),
              "end_time": r.end_time.isoformat(),
              "child_runs": []} for r in runs]

traces = to_workflow_traces(from_langsmith_traces(run_dicts))
report = analyze_pipeline(compiled, p_min=0.80, traces=traces)
```
