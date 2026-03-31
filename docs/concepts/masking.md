# The Masking Problem

*Paper reference: Section 1, "The corrector's effect on σ"; Section 3, Experiment 1*

---

Masking is the central pathology of delegated systems: **the process that preserves output quality also destroys the information needed to calibrate trust.**

## What masking looks like

Consider a code-generation pipeline. The generator produces code, a reviewer catches bugs. The dashboard shows 90% success rate. Everything looks fine.

But the generator is only 67% competent. The reviewer is catching the rest. If the reviewer degrades (model drift, changed distribution), the dashboard stays green while actual competence silently drops.

This is masking: the corrector hides the agent's weakness from the governance system.

## The masking index

$$M^* = \frac{\sigma_\text{corr}^*}{\sigma_\text{raw}^*}$$

When $M^* = 1$: no masking — what you see is what you get.
When $M^* > 1$: the system appears more competent than it is.

**Baseline masking is always present.** Even the simplest single-agent delegation has $M^* \approx 1.35$ with typical parameters. This is not a bug — it's a structural consequence of having a corrector.

```python
from minimal_oversight._formulae import (
    sigma_raw_fixed_point, sigma_corr_fixed_point, masking_index
)

sr = sigma_raw_fixed_point(0.80, eta=10, delta=2)    # 0.667
sc = sigma_corr_fixed_point(sr, catch_rate=0.70)     # 0.900
m = masking_index(sc, sr)                             # 1.35
```

## Why masking is dangerous

The danger isn't that $M^* > 1$ — it's that **governance decisions based on $\sigma_\text{corr}$ are inflated.** The paper's Experiment 1 shows that single-$\sigma$ governance (which trusts the corrected signal) over-authorizes by 36% compared to dual-$\sigma$ governance (which uses $\sigma_\text{raw}$ for authorization).

**The fix is simple:** track both signals. Authorize based on $\sigma_\text{raw}$, not $\sigma_\text{corr}$.

## Masking in chains

Masking gets worse with depth. In a linear pipeline where each layer's output feeds the next:

| Depth | $M^*$ per layer | $M^*_\text{total}$ |
|-------|-----------------|---------------------|
| 1 | 1.77 | 1.8 |
| 2 | 1.77, 1.95 | 3.5 |
| 3 | 1.77, 1.95, 2.06 | 7.1 |
| 5 | 1.77 → 2.18 | 38.3 |

The total masking grows **super-multiplicatively** — faster than $(M^*_\text{single})^D$ — because each downstream layer receives degraded input and depends more on its corrector.

## Detecting masking in practice

The package computes $M^*$ at every node and alerts when it crosses a threshold:

```python
report = analyze_pipeline(pipeline, p_min=0.80)

for alert in report.alerts:
    if "masking" in alert.message.lower():
        print(f"[{alert.level.value}] {alert.node_name}: {alert.message}")
```

!!! warning "When to worry"
    $M^* > 1.3$: monitoring recommended. Track $\sigma_\text{raw}$ separately.

    $M^* > 1.5$: corrector is doing heavy lifting. The agent may be coasting.

    $M^* > 2.0$: the dashboard is lying. Raw competence is less than half of apparent quality.

## The diagnostic differential

The pair $(\Delta\sigma_\text{raw}, \Delta M^*)$ over time tells you *what kind* of problem you have:

| $\Delta\sigma_\text{raw}$ | $\Delta M^*$ | Diagnosis | Action |
|---|---|---|---|
| Stable | Stable | Healthy | None |
| Rising | Falling | Agent improving | Reduce corrector budget |
| Falling | Rising | **Agent degrading, masked** | **Retrain agent or add capacity** |
| Falling | Falling | Correlated drift | Retrain both |
| Stable | Rising | Corrector coasting | Check if agent is coasting |
