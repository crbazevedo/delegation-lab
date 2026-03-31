# topology

Graph-aware analysis of delegation DAGs. Answers: *"Where are the structural risks in this pipeline?"*

*Paper reference: Section 1 (Table 2, Delegation graphs); Section 4 (Demonstrations 1, 3, 4)*

## detect_motifs

::: minimal_oversight.topology.detect_motifs
    options:
      show_source: false

Finds all four canonical motifs: chain, fan-out, diamond, merge.

```python
from minimal_oversight.topology import detect_motifs

for m in detect_motifs(pipeline):
    print(f"[{m.motif.value}] {m.nodes}")
    print(f"  {m.risk_description}")
```

## rank_nodes_by_risk

::: minimal_oversight.topology.rank_nodes_by_risk
    options:
      show_source: false

Ranks nodes by governance priority using the SOTA proxy score $S(v) = \text{DC}(v) \times M^*(v) \times \kappa(v)$.

```python
from minimal_oversight.topology import rank_nodes_by_risk

for r in rank_nodes_by_risk(pipeline):
    print(f"{r.name}: DC={r.delegation_centrality:.1f}, SOTA={r.sota_score}")
```

## delegation_centrality

::: minimal_oversight.topology.delegation_centrality
    options:
      show_source: false

Fan-out degree weighted by downstream depth. Nodes with high DC have the most governance leverage — a correction there propagates farthest.

## conditional_fragility

::: minimal_oversight.topology.conditional_fragility
    options:
      show_source: false

Estimates $P(D \mid A \text{ ok}) / P(D \mid A \text{ error})$ at a merge node with shared upstream source. Ratios above 1.0 indicate hidden vulnerability to correlated failures.

## Data classes

### Motif (Enum)

| Value | Pattern | Failure surface |
|-------|---------|----------------|
| `CHAIN` | A → B → C | Quality loss with depth |
| `FAN_OUT` | A → {B, C, D} | One failure → multiple branches |
| `FAN_IN` | {B, C} → D | Same as MERGE |
| `DIAMOND` | A → {B, C} → D | Correlated errors at D |
| `MERGE` | {B, C} → D | Bottleneck path |
| `SINGLE` | A | Baseline masking |

### MotifInstance

| Field | Type | Description |
|-------|------|-------------|
| `motif` | `Motif` | Which motif |
| `nodes` | `list[str]` | Involved node names |
| `risk_description` | `str` | Human-readable risk explanation |

### NodeRisk

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Node name |
| `delegation_centrality` | `float` | DC(v) |
| `masking_index` | `float \| None` | $M^*$ |
| `sota_score` | `float \| None` | $S(v) = \text{DC} \times M^* \times \kappa$ |
| `fan_out_degree` | `int` | Out-degree |
| `fan_in_degree` | `int` | In-degree |
| `is_bottleneck` | `bool` | High fan-in heuristic |
| `motifs` | `list[Motif]` | Motifs this node participates in |
