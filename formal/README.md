# Adaptive review controller — implementation & verification

The runtime ("online") review-allocation policy, its formal specification, and its
machine-checked correctness artifacts.

| Artifact | What it is | Status |
|---|---|---|
| `src/minimal_oversight/online_control.py` | Reference implementation: `Workflow`, `delivered_quality`, `marginal_node`, `online_step` (the monotone ratchet) and the optional `online_step_release` (hysteresis-release variant). Invariants documented in the module docstring. | — |
| `scripts/verify_online_control.py` | **Z3/SMT proofs** of the algebraic invariants (P1–P7: corrected/min/product/mean monotonicity, budget-cap safety, non-harmful add step) plus the release variant's P8 (release-preserves-feasibility) and P9 (deadband no-cycle). Z3 is the engine behind Dafny/SPARK/Boogie. | **PROVED** (run: `uv run --with z3-solver python scripts/verify_online_control.py`) |
| `tests/test_online_control.py` | **Property-based tests** (Hypothesis) over random DAGs: INV-BUDGET, INV-MONOTONE, INV-TERMINATE for the ratchet, and INV-BUDGET, INV-FEASIBLE, static termination (INV-NO-CYCLE) for the release variant. | **PASS** |
| `scripts/online_competitive.py` | **Competitive analysis** vs the dynamic (per-step releasing) optimum on monotone vs alternating-bottleneck drift: shows the ratchet's holding cost is not competitive under a moving bottleneck, and when the release variant's deadband+dwell earn their keep (observation noise / costly switching). | run: `PYTHONPATH=src python3 scripts/online_competitive.py` |
| `formal/AdaptiveReview.tla`, `AdaptiveReview.cfg` | **TLA+ specification** of the control loop (add + guarded release) + TLC config (BudgetSafety, FeasibilityPreserved, Termination). | Model-checkable with TLC (`tlc AdaptiveReview.tla -config AdaptiveReview.cfg`); requires Java/TLA+ tools, not run in the authoring environment. |

## Invariants

Hold for **both** controllers:

- **INV-BUDGET** — every `budget[v]` stays in `[0, b_max]`.
- **INV-TERMINATE** — a step changes one node by `delta`; the ratchet adds ≤
  `⌈n·b_max/delta⌉` increments, and the release variant's deadband (≥ one grid
  step, P9) forbids add-then-release cycles, so it settles into the band.

The **monotone ratchet** (`online_step`) additionally satisfies:

- **INV-MONOTONE** — a control step never lowers delivered quality (corrected
  quality is monotone in `b`; product/min/mean aggregations are monotone). This is
  exactly why it is *not* competitive under an alternating bottleneck: it can only
  add, so it holds peak budget on every contender forever (see `online_competitive.py`).

The optional **hysteresis-release** controller (`online_step_release`) trades
INV-MONOTONE — which it violates on purpose, releasing slack budget — for:

- **INV-FEASIBLE** (Z3 P8) — a release from a feasible state keeps `Q_G ≥ p_min`,
  via the guard `corrected(s, b_s − δ) ≥ p_min + margin`.
- **INV-NO-CYCLE** (Z3 P9) — the deadband separates the add region from the
  release region, so in a static state each sink's budget settles into the
  deadband band and stops (the Lyapunov fact behind INV-TERMINATE for the variant).

The deeper **feasibility-maintenance** property (if static feasibility holds at the
drifted skill, the controller holds `Q_G ≥ p_min`) follows from INV-MONOTONE (ratchet)
or INV-FEASIBLE (release variant) plus the autonomy-time bound; full mechanization is
future work.

## Experiments (drift / online)

- `scripts/online_review_under_drift.py` — single-workflow illustration.
- `scripts/online_competitive.py` — competitive ratio of each controller vs the
  dynamic (per-step releasing) optimum, on monotone vs alternating-bottleneck drift.
- `scripts/online_skirental.py` — **falsifiable theory test**: asserts the release
  decision is ski-rental (dwell* = 2λ, tight 2-competitive) with a matched
  noise-induced deadband floor. Write-up: [`competitive-analysis.md`](competitive-analysis.md).
- `scripts/online_tracking.py` — **prove-or-break** of the fundamental noise floor:
  the Kalman-optimal tracking lower bound `Ω(√(νσ)T)` (filter-proof for any drift).
- `scripts/online_caching.py` — **prove-or-break** of the multi-agent coupling: shared
  oversight capacity = online caching (ratchet infeasible; CR = Θ(h) det, O(log h) rand).
- `scripts/online_matchlb.py` — **prove-or-break** of the *revived* matching lower bound:
  every deterministic policy ≥ h (adaptive adversary), LRU tight, defeats the prior
  no-separation refutation under finite capacity. Honest regime stated.
- `scripts/online_testbed.py` — 8-topology testbed; paired ATE + motif heterogeneity.
- `scripts/online_random_dags.py` — Erdős–Rényi DAG ensemble (debiased motif
  contributions + VIF collinearity diagnostic). *Not* a Wishart prior: a DAG
  adjacency is binary/upper-triangular, not a covariance matrix.
