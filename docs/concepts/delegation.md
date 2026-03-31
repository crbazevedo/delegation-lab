# What is a Delegation?

*Paper reference: Section 1, "The delegation setup"*

---

A **delegation** is the simplest unit of governed autonomy. It has three parts:

1. **An agent** ($B$) that produces outputs
2. **A corrector** ($C$) that reviews a subset and fixes errors
3. **A principal** ($A$) that decides how much authority to grant

Every multi-agent pipeline is made of delegations chained together.

## Two signals, not one

The theory tracks two distinct quality measures at every delegation boundary:

| Signal | What it measures | How it's observed |
|--------|-----------------|-------------------|
| $\sigma_\text{raw}$ | **Raw competence** — agent's uncorrected success rate | Pre-correction outcomes |
| $\sigma_\text{corr}$ | **Corrected quality** — what the system actually ships | Post-correction outcomes |

**Why both matter:** If you only track $\sigma_\text{corr}$ (the output), you can't tell whether quality comes from the agent being good or the corrector catching errors. This distinction is the foundation of the entire framework.

```python
from minimal_oversight.models import Node

node = Node(
    "code_generator",
    sigma_skill=0.55,   # true competence (if known)
    sigma_raw=0.46,     # observed pre-correction success rate
    sigma_corr=0.84,    # observed post-correction success rate
    catch_rate=0.70,    # corrector catches 70% of errors
)
```

## The fixed point

Given an observation rate $\eta$ and a decay rate $\delta$, the agent's measured competence converges to:

$$\sigma_\text{raw}^* = \frac{\eta \cdot \sigma_\text{skill}}{\eta + \delta}$$

This is the Return Operator's fixed point (Equation 5). The corrected quality is:

$$\sigma_\text{corr}^* = \sigma_\text{raw}^* + (1 - \sigma_\text{raw}^*) \times c$$

where $c$ is the corrector's catch rate (Equation 6).

**Worked example:** With $\sigma_\text{skill} = 0.80$, $\eta = 10$, $\delta = 2$, $c = 0.70$:

- $\sigma_\text{raw}^* = 10 \times 0.80 / 12 = 0.667$
- $\sigma_\text{corr}^* = 0.667 + 0.333 \times 0.70 = 0.900$

The system ships at 90% quality, but the agent is only 67% competent. The 23-point gap is the corrector doing its job — and hiding the agent's weakness.

```python
from minimal_oversight._formulae import sigma_raw_fixed_point, sigma_corr_fixed_point

sr = sigma_raw_fixed_point(0.80, eta=10, delta=2)  # 0.667
sc = sigma_corr_fixed_point(sr, catch_rate=0.70)    # 0.900
```

## The Axiom of Minimal Oversight

*Paper reference: Section 1, "The Axiom of Minimal Oversight (AMO)"*

The AMO says: **minimize the total cost of oversight, subject to meeting a quality target.** The cost is measured in Fisher information geometry — a principled way to weight governance effort by how informative it is.

The result is a water-filling allocation: spend more oversight where the agent is moderately competent ($\sigma \approx 0.75$), less where it's very weak (review is wasted) or very strong (review finds nothing). This parallels Shannon's power allocation across channels.

$$\alpha^*(x) = \min\left(\alpha_\text{max}, \frac{\lambda}{2} \sigma_\text{raw}(x) \sqrt{\sigma_\text{raw}(x)(1 - \sigma_\text{raw}(x))}\right)$$

The key insight: **oversight is not a uniform slider.** It's a resource that should be allocated where it produces the most quality improvement per unit of governance cost.
