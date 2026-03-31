# models

Core data models for governed delegation. These are the typed objects you construct to describe your pipeline.

## Node

::: minimal_oversight.models.Node
    options:
      show_source: false
      members: false

A single delegation node (agent + optional corrector).

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Human-readable identifier |
| `sigma_skill` | `float \| None` | True competence (if known) |
| `sigma_raw` | `float \| None` | Observed raw competence (pre-correction) |
| `sigma_corr` | `float \| None` | Observed corrected quality (post-correction) |
| `catch_rate` | `float \| None` | Corrector's error-catch probability $c$ |
| `review_capacity` | `float \| None` | Fraction of outputs reviewed ($K/N$) |
| `drift_rate` | `float \| None` | Skill degradation rate $\mu_\text{eff}$ |
| `noise_var` | `float \| None` | Noise variance $\nu_\text{eff}^2$ |
| `aggregation` | `AggregationType` | How this node merges inputs (for merge nodes) |
| `metadata` | `dict` | Arbitrary extra data |

**Property:** `node.masking_index` returns $M^* = \sigma_\text{corr} / \sigma_\text{raw}$ (or `None` if either signal is missing).

```python
from minimal_oversight.models import Node

gen = Node(
    "code_generator",
    sigma_skill=0.55,
    catch_rate=0.65,
    review_capacity=0.50,
)
```

## AggregationType

::: minimal_oversight.models.AggregationType
    options:
      show_source: false
      members: true

How a merge node combines inputs from its parents:

- `PRODUCT` — errors compound multiplicatively (default, most common)
- `WEAKEST_LINK` — limited by worst parent (most fragile, most honest)
- `WEIGHTED_MEAN` — weighted average (dilutes both errors and masking)

## PipelineGraph

::: minimal_oversight.models.PipelineGraph
    options:
      show_source: false
      members: false

A delegation DAG: nodes connected by directed edges. Wraps `networkx.DiGraph`.

| Method | Returns | Description |
|--------|---------|-------------|
| `add_node(node)` | | Add a Node to the graph |
| `add_edge(source, target)` | | Add a directed edge |
| `get_node(name)` | `Node` | Look up a node by name |
| `nodes` | `dict[str, Node]` | All nodes |
| `depth` | `int` | Longest path length |
| `sources()` | `list[str]` | Entry points (no parents) |
| `sinks()` | `list[str]` | Output points (no children) |
| `parents(name)` | `list[str]` | Parent node names |
| `children(name)` | `list[str]` | Child node names |
| `fan_out(name)` | `int` | Out-degree |
| `fan_in(name)` | `int` | In-degree |
| `topological_order()` | `list[str]` | Topologically sorted names |
| `graph` | `nx.DiGraph` | Underlying networkx graph |

```python
from minimal_oversight.models import Node, PipelineGraph, AggregationType

gen = Node("generator", sigma_skill=0.55, catch_rate=0.65)
rev = Node("reviewer", sigma_skill=0.60, catch_rate=0.70)
merge = Node("merge", sigma_skill=0.55, aggregation=AggregationType.PRODUCT)

pipeline = PipelineGraph([gen, rev, merge])
pipeline.add_edge("generator", "reviewer")
pipeline.add_edge("reviewer", "merge")

print(pipeline)           # PipelineGraph(nodes=3, edges=2, depth=2)
print(pipeline.depth)     # 2
print(pipeline.sources()) # ['generator']
print(pipeline.sinks())   # ['merge']
```

## GovernancePolicy

::: minimal_oversight.models.GovernancePolicy
    options:
      show_source: false
      members: false

Parameters governing a delegation. Optional — `analyze_pipeline()` accepts `p_min` directly.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `p_min` | `float` | 0.80 | Minimum acceptable quality target |
| `review_budget` | `float \| None` | `None` | Average review-cost budget $B$ |
| `alpha_max` | `float` | 1.0 | Maximum authority any node can receive |
| `routing_rule` | `str \| None` | `None` | Routing policy description |
| `scope_rule` | `str \| None` | `None` | Scope policy description |
| `intervention_thresholds` | `dict` | `{}` | Per-node or global alert thresholds |

## WorkflowTrace

::: minimal_oversight.models.WorkflowTrace
    options:
      show_source: false
      members: false

A single observed item passing through the pipeline. Used by the estimation module to compute $\sigma_\text{raw}$, $\sigma_\text{corr}$, and $M^*$ from logs.

| Attribute | Type | Description |
|-----------|------|-------------|
| `task_id` | `str` | Unique item identifier |
| `node_outcomes` | `dict[str, float]` | Node → pre-correction outcome (0/1) |
| `node_corrected` | `dict[str, float]` | Node → post-correction outcome |
| `routing_path` | `list[str]` | Ordered list of nodes visited |
| `timestamps` | `dict[str, float]` | Node → processing timestamp |
| `was_reviewed` | `dict[str, bool]` | Node → whether corrector reviewed |
| `human_intervention` | `bool` | Whether a human intervened |

In production, these are created by the [trace parsers](../guides/traces.md). For manual construction:

```python
from minimal_oversight.models import WorkflowTrace

trace = WorkflowTrace(
    task_id="item_001",
    node_outcomes={"generator": 1.0, "reviewer": 0.0},
    node_corrected={"generator": 1.0, "reviewer": 1.0},
    routing_path=["generator", "reviewer"],
    was_reviewed={"generator": False, "reviewer": True},
)
```
