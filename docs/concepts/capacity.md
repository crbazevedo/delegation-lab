# Delegation Capacity

*Paper reference: Section 1, "Delegation capacity"; Theorem 1*

---

Before optimizing review allocation or tuning a corrector, ask the most basic question: **can this pipeline hit the target quality at all?**

## The operational ceiling

The delegation capacity $C_\text{op}$ is the best possible output quality the
pipeline can achieve under the stated model, topology, and budget. If the
quality target $p_\text{min}$ exceeds $C_\text{op}$, local governance tuning
alone cannot rescue the design; capability, review budget, task decomposition,
or topology must change.

$$C_\text{op}(G, K, B) = \sup_{p(\text{task})} q^*(\text{output})$$

Here $q^*(\text{output})$ is the shipped output quality at the sink after
available correction. Raw support $\sigma_\text{raw}$ remains the authorization
signal because it is the less masked estimate of agent competence.

```python
from minimal_oversight.capacity import check_feasibility

report = check_feasibility(pipeline, p_min=0.80)
print(report.explanation)
# INFEASIBLE: Quality target p_min=0.800 exceeds pipeline
# capacity C_op=0.725. Within the fixed model, topology, and
# budget, no local governance policy can rescue this design.
```

!!! danger "When the AMO has no solution"
    If $p_\text{min} > C_\text{op}$, the theory prescribes **no delegation** — not "more authority." The task must be performed by a more capable agent, decomposed into subtasks, or the topology must change.

## For a single node

A single node with observation rate $\eta$, decay/reversion rate $\delta$, and
baseline support $\sigma_0$ achieves maximum capacity when
$\sigma_\text{skill} = 1$:

$$C = \frac{\eta + \delta\sigma_0}{\eta + \delta}$$

With the conservative $\sigma_0=0$ default, $\eta = 10$, and $\delta = 2$,
$C = 0.833$. This is the ceiling even for a perfect agent because stale
evidence and environment shift pull measured support back toward the baseline.

## For a chain

Each layer degrades the signal. The recursive formula accounts for the fact that each corrector stabilizes quality before passing it downstream:

$$\sigma_\text{corr}^*(i) = R\big(\sigma_\text{skill} \times \sigma_\text{corr}^*(i-1)\big), \quad \sigma_\text{corr}^*(0) = 1$$

where $R(\cdot)$ is the Return Operator at fixed point (Equation 11).

??? example "Verify the math"
    ```python
    from minimal_oversight._formulae import recursive_chain_quality

    # How does quality degrade with depth?
    for D in range(1, 8):
        q = recursive_chain_quality(D, sigma_skill=0.55, catch_rate=0.65, eta=10, delta=2)
        print(f"D={D}: C_op = {q:.3f}")
    ```

The theory-observation gap is less than 0.002 across all 28 conditions tested in the paper (Experiment 6).

!!! note "Correction model: theory vs simulation"
    The closed-form equations (Eq. 5-6) use raw $c$ as the catch rate. The paper's simulator uses $c \times K/N$ as the effective catch rate, where $K/N$ is the fraction of outputs reviewed. This means:

    - **Theoretical $M^*$ = 1.83** (with $c = 0.70$, Eq. 6)
    - **Simulated $M^*$ ≈ 1.4** (with $c \times K/N = 0.70 \times 0.50 = 0.35$)

    If your observed $M^*$ is lower than the theoretical prediction, check your effective review coverage.

## Critical depth

There is a maximum target-feasible depth beyond which adding layers drives the
recursive corrected-chain quality below the required target:

$$D_\text{max} = \max\{D: C_\text{op}(D) \geq p_\text{min}\}$$

This is computed directly from the recursive formula (Eq. 11). For
$\sigma_\text{skill} = 0.55$, $c = 0.65$, and the conservative $\sigma_0=0$
default, a demanding target $p_\text{min}=0.80$ permits one layer but not two.
A lower target such as $p_\text{min}=0.50$ has no finite cliff in the
stabilized corrected-chain model.

**Better correctors extend the useful depth significantly** because each layer
passes a more reliable corrected signal downstream.

## The effective autonomy buffer

The buffer combines capacity, quality target, and workflow complexity into one number:

$$B_\text{eff} = C_\text{op} - p_\text{min} - \lambda H(W)$$

- $B_\text{eff} > 0$: delegated autonomy is feasible
- $B_\text{eff} = 0$: at the autonomy cliff
- $B_\text{eff} < 0$: the fixed design lacks sufficient margin to maintain quality

The complexity tax $\lambda H(W)$ captures how routing entropy, tool-call variability, and timing uncertainty consume the quality margin. Each additional bit of process entropy costs approximately $\lambda \approx 0.02$ in quality (Experiment 7).
