# Topology as Governance

*Paper reference: Section 1, "Topology as a governance object"; Table 2*

---

The pipeline DAG is not just a wiring diagram — it determines where governance has leverage, how errors propagate, and what kind of intervention is structurally worthwhile.

## Four canonical motifs

| Motif | Structure | Failure surface | Governance action |
|-------|-----------|----------------|-------------------|
| **Chain** | A → B → C | Quality and masking accumulate with depth | Improve upstream first |
| **Fan-out** | A → {B, C, D} | One failure contaminates all branches | Prioritize the fan-out node |
| **Diamond** | A → {B, C} → D | Correlated errors at D when A fails | Fix A, not D |
| **Merge** | {B, C} → D | Throughput limited by bottleneck path | Invest where $\partial C_\text{op}/\partial c(v)$ is largest |

```python
from minimal_oversight.topology import detect_motifs

motifs = detect_motifs(pipeline)
for m in motifs:
    print(f"[{m.motif.value}] {m.risk_description}")
```

## Delegation centrality

**DC(v)** measures how many downstream nodes are affected by a correction at $v$. A node with high fan-out and deep descendants has high centrality — improving it has outsized impact.

The **SOTA priority score** combines centrality with masking and task complexity:

$$S(v) = \text{DC}(v) \times M^*(v) \times \kappa(v)$$

where $\kappa(v) = 1 - \sigma_\text{skill}(v)$ is the task complexity. The node with the highest $S(v)$ benefits most from an expensive model upgrade.

```python
from minimal_oversight.topology import rank_nodes_by_risk

risks = rank_nodes_by_risk(pipeline)
for r in risks:
    print(f"{r.name}: DC={r.delegation_centrality:.1f}, SOTA={r.sota_score}")
```

## Fan-out amplification

When a fan-out node's corrector is removed, errors propagate to **all children simultaneously**. In the SDLC pipeline, removing the reviewer's corrector creates three simultaneous cascades at test, requirements, and security.

This is why the SOTA model should go to the **corrector at the fan-out node**, not the executor at the generator. The corrector's improvement propagates to all branches; the executor's improvement is local.

The paper's Demonstration 1 formalizes this as the SOTA priority score. In the SDLC pipeline (Notebook 1), placing the expensive model as corrector at the reviewer yields ~10× more system improvement than placing it as executor at the generator ($\Delta C_\text{op}$: +0.008 vs +0.0008), because the corrector's improvement propagates through all three downstream branches.

## Conditional fragility (diamond pattern)

In a diamond (A → {B, C} → D), B and C share a common upstream source. When A fails, **both** B and C receive degraded input — their errors are correlated, not independent.

Average quality comparisons miss this: the difference between correlated and independent error sources is less than 1%. But conditioning on A's failure reveals a 1.4x fragility ratio:

$$\frac{P(D \text{ correct} \mid A \text{ correct})}{P(D \text{ correct} \mid A \text{ error})} \approx 1.4\times$$

The prescription: **fix A upstream** rather than adding redundancy at D. Redundant voters at D fail on the same cases when the errors are correlated.

```python
from minimal_oversight.topology import conditional_fragility

ratio = conditional_fragility(pipeline, "merge_node", parent_corrs, shared_catch_rate)
print(f"Fragility ratio: {ratio:.1f}x")
```

## Optimal DAG shape

Should a pipeline be deep and narrow or wide and shallow?

- **Depth** costs capacity: each layer adds masking, and beyond $D_\text{max}$ quality saturates
- **Width** costs resilience: each fan-out branch amplifies cascade risk

The optimal shape is a **pyramid**: wide at the top (cheap agents with voting), narrow in the middle (capable specialists), and redundant at the merge gate (multiple evaluators with independent error sources).
