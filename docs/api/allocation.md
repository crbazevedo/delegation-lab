# allocation

Optimization and policy support. Answers: *"Where should I place review effort?"* and *"What should change?"*

*Paper reference: Section 1 (AMO, Eq. 2, 8); Section 4 (Algorithm 1, Demonstrations 1-2)*

## solve_amo

::: minimal_oversight.allocation.solve_amo
    options:
      show_source: false

Solves the Axiom of Minimal Oversight — the water-filling optimization that allocates oversight proportionally to $\sigma \sqrt{\sigma(1-\sigma)}$, peaking at $\sigma \approx 0.75$.

```python
from minimal_oversight.allocation import solve_amo
import numpy as np

sigma = np.array([0.30, 0.55, 0.75, 0.90])
result = solve_amo(sigma, p_min=0.60)

for s, a in zip(sigma, result.alpha_star):
    print(f"σ = {s:.2f} → α* = {a:.3f}")
# Peak allocation at σ = 0.75 (highest marginal return of review)
```

## recommend_governance_changes

::: minimal_oversight.allocation.recommend_governance_changes
    options:
      show_source: false

The high-level recommendation engine. Combines capacity analysis, topology, and intervention priority into an ordered list of actions.

```python
from minimal_oversight.allocation import recommend_governance_changes

for r in recommend_governance_changes(pipeline, p_min=0.80):
    print(f"{r.priority}. [{r.target_node}] {r.action}")
    print(f"   {r.rationale}")
```

## select_scope

::: minimal_oversight.allocation.select_scope
    options:
      show_source: false

Endogenous scope selection (the outer AMO problem): which tasks should be delegated at all? Without a coverage constraint, the optimizer cherry-picks the easiest tasks. With `coverage_min`, it forces broader delegation.

## prioritize_intervention

::: minimal_oversight.allocation.prioritize_intervention
    options:
      show_source: false

Ranks nodes by the SOTA proxy $S(v) = \text{DC}(v) \times M^*(v) \times \kappa(v)$ when exact sensitivities ($\partial T_\text{auto}^* / \partial c(v)$) are unavailable.

## Data classes

### AllocationResult

| Field | Type | Description |
|-------|------|-------------|
| `alpha_star` | `np.ndarray` | Optimal authority allocation |
| `sigma_raw` | `np.ndarray` | Input competence values |
| `lam` | `float` | Lagrange multiplier (water level) |
| `total_cost` | `float` | Governance cost $\int \alpha^2 \sqrt{g}\, dx$ |
| `delivery` | `float` | Achieved delivery $\int \alpha \sigma\, dx$ |

### ScopeRecommendation

| Field | Type | Description |
|-------|------|-------------|
| `delegated_tasks` | `list[int]` | Indices of tasks to delegate |
| `excluded_tasks` | `list[int]` | Indices to retain/route elsewhere |
| `coverage` | `float` | Fraction delegated |
| `total_cost` | `float` | Governance cost of delegated subset |
| `avg_sigma_delegated` | `float` | Mean competence of delegated tasks |
| `explanation` | `str` | Human-readable summary |

### GovernanceRecommendation

| Field | Type | Description |
|-------|------|-------------|
| `priority` | `int` | Rank (1 = most urgent) |
| `action` | `str` | What to do |
| `target_node` | `str \| None` | Which node (or `None` for pipeline-wide) |
| `rationale` | `str` | Why this action matters |
| `expected_impact` | `str` | What improvement to expect |
