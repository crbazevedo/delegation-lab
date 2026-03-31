# Autonomy Time

*Paper reference: Section 1, "Autonomy time"; Proposition 3; Experiment 8*

---

Once you know the pipeline is feasible ($B_\text{eff} > 0$), the operational question is: **how long can it run without human intervention?**

## The formula

$$T_\text{auto}^* = \frac{B_\text{eff}}{\mu_\text{eff}}$$

where:

- $B_\text{eff} = C_\text{op} - p_\text{min} - \lambda H(W)$ is the effective autonomy buffer
- $\mu_\text{eff}$ is the drift rate (how fast the environment changes)

In words: autonomy time is the safety margin divided by how fast that margin erodes.

??? example "Verify the math (Motif 1 worked example)"
    ```python
    from minimal_oversight._formulae import autonomy_time

    t = autonomy_time(
        c_op=0.833,        # single-node capacity (η=10, δ=2)
        p_min=0.50,        # quality target
        lam=0.02,          # governance gap coefficient
        h_w=0.0,           # process entropy (bits)
        mu_eff=0.005,      # drift rate
    )
    print(f"T*_auto = {t:.0f} time units")  # 66.6
    ```

## Five factors of autonomy

$T_\text{auto}^*$ increases when:

1. **$C_\text{op}$ is high** — better agents, better correctors, simpler topology
2. **$p_\text{min}$ is low** — relaxed quality requirements give more margin
3. **$H(W)$ is low** — simpler, more deterministic workflows
4. **$\lambda$ is small** — better governance compresses the complexity tax
5. **$\mu_\text{eff}$ is small** — stable models, large scope, frequent observations

## The 1/μ scaling law

The paper's Experiment 8 confirms that $T_\text{auto}^* \propto 1/\mu$ over two orders of magnitude of drift rate. The log-log slope is $-0.99$ (predicted: $-1.0$).

This is a usable scheduling law: if you know the drift rate, you know how often to intervene.

## The capacity cliff

There's a critical process entropy beyond which autonomous operation becomes impossible:

$$H_\text{crit} = \frac{C_\text{op} - p_\text{min}}{\lambda}$$

Below $H_\text{crit}$: autonomous operation works ($T_\text{auto}^* > 0$).
Above $H_\text{crit}$: continuous human oversight required, regardless of governance policy.

This is a **phase transition**, not a gradual trade-off. As $H(W) \to H_\text{crit}$, the buffer shrinks quadratically in $T_\text{auto}^*$, so autonomy time collapses rapidly near the cliff.

!!! tip "Practical implication"
    Every tool-call decision, routing branch, and conditional path adds process entropy. The cliff means there is a **hard limit** on how complex an autonomous workflow can be within a fixed architecture. The path to more complexity runs through increasing $C_\text{op}$ (better agents/correctors) and decreasing $\lambda$ (better governance), not through ignoring the constraint.

## Intervention scheduling

The minimum review frequency at each node is $f(v) = 1/T_\text{auto}^*(v)$:

```python
report = analyze_pipeline(pipeline, p_min=0.80)

for s in report.intervention_schedule:
    print(f"{s.node_name}: review every {s.t_auto:.0f} steps (rank {s.priority_rank})")
```

Nodes with short $T_\text{auto}^*$ (high drift, high process entropy, low capacity) need frequent review. Nodes with long $T_\text{auto}^*$ can operate autonomously for extended periods.
