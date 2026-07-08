# Online review control

A fixed oversight allocation goes stale when competence drifts during deployment: a node that
was the bottleneck recovers, another degrades, and review that was well placed is now wasted or
missing. The adaptive controller re-allocates review at runtime — adding the least review needed to
hold a delivered-quality target, and releasing review that is no longer needed.

## Base controller

`minimal_oversight.online_control` provides two one-step policies over a `Workflow`:

- **`online_step`** — the monotone marginal *ratchet*: when delivered quality dips below the target
  `p_min`, add one review increment `delta` to the node with the largest marginal effect on the
  bottleneck sink. It only ever adds (INV-MONOTONE), so it is ideal for a single, monotonically
  degrading bottleneck.
- **`online_step_release`** — a hysteresis-guarded *release* variant: it also frees review from a
  persistently-slack node, so committed review tracks an *alternating* bottleneck instead of piling
  up on every contender.

Safety is machine-checked independently of performance: INV-BUDGET, INV-MONOTONE, INV-FEASIBLE,
INV-NO-CYCLE, INV-TERMINATE (Z3 obligations in `scripts/verify_online_control.py`; a TLA+
specification in `formal/AdaptiveReview.tla`).

## Variants

### Ski-rental release — `minimal_oversight.skirental`

Holding idle review is *rent* (cost per step); releasing and later re-acquiring it is *buy*
(switching cost `2·lambda`). With the slack duration unknown, the release decision is online
ski-rental. The optimal hysteresis dwell is `2·lambda`, which is `2 − 1/(2·lambda)`-competitive; no
fixed dwell does better against an adversarial slack length.

**Concrete instance — a RAG agent under continuous drift.** A support agent retrieves over a vector
DB that grows on its own (new docs ingested) while the customer query distribution shifts on its own
(new topics emerge). A topic the agent had mastered stays reliable only until the next organic shift
outruns its coverage. When a topic recovers, holding a verification pass on it is *rent*; switching
verification off and later re-establishing it — re-pointing the judge, rebuilding the topic's rubric
— is the `2·lambda` *buy*. Because coverage drifts continuously and unscheduled, the stable duration
is genuinely unknown.

The closed forms are **scenario-agnostic**: `dwell* = 2·lambda` and the `2 − 1/(2·lambda)` ratio
depend only on the rent/buy structure, not on *why* competence drifts. What the scenario must supply
is the result's *hypothesis* — an **unknown, possibly-adversarial slack duration**. A scheduled
change (a planned migration) is partly predictable and collapses toward offline optimization;
continuous endogenous drift is genuinely online, which is what makes `2·lambda` the right dwell
rather than overkill.

```python
from minimal_oversight.skirental import skirental_dwell, skirental_ratio, minimax_dwell

skirental_dwell(lam=10)   # 20.0 — hold a slack node 2·lambda steps before releasing
skirental_ratio(lam=10)   # 1.95 — the competitive ratio at the optimal dwell
minimax_dwell(lam=10)     # (20.0, 1.95) — the minimizing dwell and its worst-case ratio
```

### Tracking under noise — `minimal_oversight.tracking`

Competence is observed with noise and itself drifts. For random-walk drift (`nu`) plus Gaussian
observation noise (`sigma`), the Kalman filter is the MMSE-optimal causal estimator. Staying
feasible with high probability needs a margin above the estimate, and that holding overhead has an
irreducible per-step floor of order `sqrt(nu·sigma)` that no filter removes — the unfiltered
deadband is a factor `sqrt(sigma/nu)` worse.

```python
from minimal_oversight.tracking import KalmanTracker, noise_floor_per_step, deadband_margin

kt = KalmanTracker(nu=0.02, sigma=0.20)
held = kt.feasible_budget(observation)   # estimate + matched feasibility margin
noise_floor_per_step(0.02, 0.20)         # the irreducible per-step holding floor
deadband_margin(0.20)                    # the unfiltered margin (sqrt(sigma/nu) larger)
```

### Shared-pool caching — `minimal_oversight.caching`

When several nodes contend for one *finite shared review pool* of size `h = floor(C / b*)`, release
becomes online paging. Deterministic LRU eviction is `Theta(h)`-competitive; randomized MARKER is
`O(log h)`; and the never-release ratchet is *infeasible* once more than `h` nodes have been the
bottleneck.

```python
from minimal_oversight.caching import (
    SharedPoolController, pool_capacity, competitive_ratio, cyclic_adversary,
)

h = pool_capacity(C=2.0, b_star=1.0)             # 2
ctrl = SharedPoolController(h, policy="marker")  # or "lru"
ctrl.request(bottleneck_sink)                    # (re)fund it, evicting if the pool binds
competitive_ratio("lru", cyclic_adversary(8, 200), h=8)   # ~8 — CR tracks the pool size
```

## Validation

Every closed form and competitive ratio is checked by the prove-or-break scripts
(`scripts/online_skirental.py`, `online_tracking.py`, `online_caching.py`, `online_matchlb.py`) and
the unit tests (`tests/test_skirental.py`, `test_tracking.py`, `test_caching.py`), which *assert*
the analytic values so a wrong claim breaks the run.
