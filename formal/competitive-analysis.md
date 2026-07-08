# Competitive analysis of online review allocation under drift

The salvageable theory kernel behind the adaptive controller. Everything here is
validated by `scripts/online_skirental.py` (which **asserts** the simulator equals
the closed forms, so a wrong claim breaks the run) and motivated empirically by
`scripts/online_competitive.py`.

## Model (required-budget space — exact, not an approximation)

`corrected(s, b) = σ_s + (1−σ_s)·c·f·b` is **linear** in budget, so a sink is
feasible iff `b_s(t) ≥ r_s(t)`, where `r_s(t) = max(0, (p_min − σ_s)/((1−σ_s)c f))`
is the **minimal feasible budget**. Drift moves `r_s(t)`. The controller picks
`b_s(t)`; cost over a horizon is

```
cost = holding + λ·switching = Σ_t Σ_s b_s(t)  +  λ·Σ_t Σ_s |b_s(t) − b_s(t−1)|.
```

Competitive ratio CR = cost(policy) / cost(clairvoyant OPT). OPT knows the whole
`r` trajectory; the online policy sees a noisy observation `r̂_s(t) = r_s(t) + N(0,σ²)`.

## Prop 1 — the monotone ratchet is **not** competitive (motivation, not the result)

On a single sink that is needed briefly (`W` steps) then slack (`τ` steps), repeated,
the ratchet (`online_step`, add-only) holds `b*` from first need to the end:
`holding = b*·T`. For `τ ≥ 2λ`, OPT releases each slack phase, holding only
`b*·W·(n+1)`. Hence

```
CR_ratchet  =  Θ(τ / (W + λ))  =  Θ(1/duty),     duty = W/(W+τ),
```

**unbounded** as the duty cycle falls. *Validated:* CR = 14.9 at duty 0.003. This is
the "5–23×" from `online_competitive.py`, explained: it is a low-duty effect, and it
is essentially tautological — a policy that never releases is bad when OPT must release.

## Thm 2 — the release decision is **ski-rental**; dwell* = 2λ is tight 2-competitive

When a sink goes slack, holding its budget is **rent** (`b*`/step); releasing and
later re-acquiring it (the bottleneck returns) is **buy** (`2λ·b*`: release + readd).
The slack duration is unknown, so this is exactly **online ski-rental / rent-or-buy**.

- **Reduction.** Per slack phase: `OPT_slack(τ) = b*·min(τ, 2λ)`;
  a dwell-`d` policy pays `b*·min(d−1, τ) + 2λ·b*·1[d ≤ τ]`. *(Both verified exactly
  by the simulator.)*
- **Lower bound.** No deterministic online policy beats `2 − 1/(2λ)`-competitive
  (classic ski-rental; the release decision is a 1-D stopping time, so a threshold
  is optimal and the minimax threshold is where rent-so-far = buy).
- **Upper bound.** dwell `d* = 2λ` achieves `CR = 2 − 1/(2λ) < 2` on every instance.
  **The hysteresis dwell timer is exactly the ski-rental threshold.**

*Validated:* minimax over dwell is at `d* = 2λ = 20` with worst-case slack
`CR = 1.950 = 2 − 1/(2·10)`, to the digit. *(Randomized dwell gives `e/(e−1) ≈ 1.58`
by randomized ski-rental — a natural extension, not yet done.)*

This is the non-tautological core: the problem is structurally ski-rental, the
optimal online constant is 2, and the controller's dwell knob is the optimal threshold.

## Thm 3 — observation noise forces a **matched** deadband floor

The controller must keep `b_s ≥ r_s` (true) but sees `r̂_s = r_s + N(0,σ²)`. Holding
`b = r̂ + m` is feasible w.p. ≥ 1−δ iff `m ≥ z_δ·σ` (`z_δ = Φ⁻¹(1−δ)`). That margin
is held every step → additive holding overhead `≥ z_δ·σ·T` for a **bounded-memory**
controller; the deadband-margin policy with `m = z_δ·σ` **matches** it.

*Validated:* at fixed feasibility (`m = z·σ`), `overhead/σ` is constant across a
σ-sweep (overhead exactly linear in σ); the deadband is the matching upper bound.

## Thm 3' — the noise floor is **fundamental** (filter-proof), not bounded-memory

Can a filter average the noise away? Averaging `W` steps cuts noise to `σ/√W` but
lags a drifting target, so drift caps the window. The clean rigorous instance is
random-walk drift (increment std `ν`) plus Gaussian noise `σ`, for which the
**Kalman filter is MMSE-optimal among all causal estimators** (conditional mean =
Kalman for linear-Gaussian). Its steady-state error is therefore a hard lower bound:

```
P* = (−ν² + √(ν⁴ + 4 ν²σ²)) / 2 ,    √P* → √(ν·σ)   for ν ≪ σ.
```

**Thm 3' (fundamental floor).** Every causal controller holding feasibility w.p.
≥ 1−δ pays holding regret `≥ z_δ·√P*·T = Ω(√(ν·σ)·T)`, and a Kalman-filter + margin
controller **matches** it. The unfiltered deadband (`online_step_release`) pays
`z_δ·σ·T` — larger by `√(σ/ν)`; filtering closes the gap to the floor but, for any
drift `ν > 0`, cannot remove it. *(Worst-case Lipschitz drift of slope ν gives the
stronger rate `σ^{2/3}ν^{1/3}`; the random walk is the clean provable case.)*

*Validated* (`scripts/online_tracking.py`, which **breaks** the theorem if it can):
Kalman RMSE = √P* to 3 digits; **no** causal estimator (moving averages, EWMA, raw)
beats it; the regret floor scales as `√(ν·σ)` (constant to within 1.1× over a (ν,σ)
sweep); the deadband→Kalman margin gain is `√(σ/ν)`.

So the deadband/dwell is the *simple, unfiltered* matched policy (within `√(σ/ν)` of
optimal); the *optimal* controller adds a Kalman estimator and still cannot escape
`Ω(√(νσ)T)`. The noise contribution has both a lower bound and its matching policy.

## Thm 4 — the multi-agent coupling is **online caching** (shared oversight capacity)

The single-sink results above are the *published single-agent* kernel
(arXiv:2606.15563). With delivered quality `min` over sinks, feasibility is
per-sink (`b_s ≥ r_s`), so the k-sink problem **separates** into k independent
ski-rentals — *unless* the sinks share a resource. They do: *minimal* oversight
means a **finite review pool** `C` the agents compete for. Let `h = ⌊C/b*⌋` (how
many bottleneck-level sinks fit at once). Under drift the bottleneck moves, so the
controller reallocates scarce capacity — exactly **online caching / paging**:

```
page in cache  ↔  sink currently funded        cache size h  ↔  C/b*
page request   ↔  a sink becomes the bottleneck  cache miss   ↔  re-fund a released sink (2λb*)
```

- **C1 — the ratchet is INFEASIBLE, not just suboptimal.** It holds budget on every
  sink ever bottlenecked → demands `k·b* > C` once `k > h`. Release is *required*.
- **C2 — deterministic release is Θ(h)-competitive.** LRU eviction matches the
  classic paging bound; the cyclic adversary achieves it. *Validated:* CR = 1.99,
  2.97, 3.95, 5.86, 7.76 for h = 2,3,4,6,8 — the competitive ratio **is** the
  oversight-pool size.
- **C3 — randomized release is O(log h)-competitive.** MARKER gives an *exponential*
  improvement. *Validated:* CR = 2.06, 2.68, 3.28, 3.88 for h = 4,8,16,32, matching
  the harmonic numbers `H_h`, vs LRU's 3.98, 7.88, 15.45, 29.73. This lever
  (randomize over *which agent* to release) has **no single-sink analogue.**
- **C4 — identity noise forces infeasibility under a tight pool.** Misreading *which*
  sink is binding (the noisy `argmin`) leaves the true bottleneck unfunded; with no
  spare slot the controller cannot hedge. *Validated:* infeasibility 0→3.8→8.6→12.2%
  as misID rate rises, but **~0% with one spare slot** — slack capacity buys
  robustness to identity noise. (Clean composition with the √(νσ) floor =
  paging-with-noisy-predictions: open.)

So the **multi-agent competitive ratio is the oversight-pool size `h`** (deterministic),
exponentially reducible to `log h` by randomization, with a capacity–noise tradeoff
on top. This is the genuinely multi-agent content (it vanishes at h = ∞ / one sink).

## Thm 5 — the **revived matching lower bound** (defeats the prior refutation)

A prior analysis *refuted* the online matching lower bound: the causal policy
"commit `b_max` and hold" ties OPT, so there is no online–offline separation
(`F-T2-REFUT`). **That policy is infeasible under finite capacity:** holding `b*` on
every sink ever bottlenecked needs `k·b* > C = h·b*` once `k > h`. Remove the illegal
policy and the separation returns, as the classic paging lower bound.

**Thm 5.** Under a binding oversight pool of `h` slots, in the switching-dominated
regime, against worst-case (adaptive) drift:

- **(LB, all policies)** every *deterministic* online release policy has competitive
  ratio `≥ h`. *Proof:* the adaptive adversary requests, each step, the one sink the
  policy has not funded → the policy misses every step; the offline optimum (Belady)
  funds the farthest-future sink and misses ≤ once per `h` steps; ratio ≥ h. ∎
- **(UB)** LRU achieves `≤ h` on every sequence (classic) → **exactly h-competitive**.
- **(RAND)** MARKER is `O(H_h) = O(log h)`; every randomized policy is `Ω(log h)`
  (classic). An *exponential* improvement available only because there are k agents
  to randomize over — no single-sink analogue.
- **(REVIVAL)** the `F-T2-REFUT` witness is infeasible under capacity, so it cannot
  certify no-separation; the separation is `Θ(h)` (det) / `Θ(log h)` (rand).

*Validated* (`scripts/online_matchlb.py`): LRU/FIFO are tight at CR = h (2.99, 4.98,
7.89 for h = 3,5,8) while worse policies (MRU) blow up — none beats h; LRU = h on the
adversary, ≪ h (1.5–2.6) on benign drift; MARKER = H_h ≪ h; commit-and-hold demands
k·b* > C.

**Honest regime (stated, not buried).** The `Θ(h)` ratio is for **switching-dominated
cost** and **worst-case drift**. The total-cost CR → h only as `λ` (re-tasking cost)
dominates the rent; when holding dominates, the binding pool forces equal holding and
CR → 1 (no separation). Under benign (stochastic) drift CR ≪ h. So the revived bound
says: *when re-tasking oversight is expensive and the bottleneck moves adversarially,
finite oversight is provably `h`-competitive and no policy escapes it* — and that is
exactly the realistic "minimal oversight" regime. The result is a clean reduction to
classical paging; the contribution is the reduction + the revival, not a new bound.

## What is solid vs open

| Result | Status |
|---|---|
| Prop 1 (ratchet Θ(1/duty)) | proven + validated; but tautological (motivation only) |
| Thm 2 (ski-rental, tight 2-competitive, dwell*=2λ) | **rigorous reduction + validated to the digit** |
| Thm 3, unfiltered deadband floor `Ω(σT)` + matched deadband | proven + validated |
| Thm 3', **fundamental** noise floor `Ω(√(νσ)T)` (Kalman-optimal lower bound + Kalman-matched upper bound) | **resolved + validated** (was the decisive gap) |
| Thm 3', worst-case Lipschitz rate `σ^{2/3}ν^{1/3}` | known minimax rate; clean proof for this problem not yet written |
| Thm 4 (shared capacity = caching; CR = Θ(h) det, O(log h) rand; ratchet infeasible) | **reduction + validated** (C1–C3); this is the multi-agent content |
| Thm 5 (revived matching LB: every det policy ≥ h, LRU tight, defeats F-T2-REFUT) | **proven (reduction to classic paging LB) + validated**; conditional on switching-dominated + worst-case drift |
| Thm 4, identity-noise × capacity tradeoff (C4) | validated qualitatively; clean paging-with-noisy-predictions bound **open** |
| DAG topology beyond independent competing sinks (interior nodes, shared sub-reviews) | **OPEN** |
| Stackelberg / strategic agents (honest-gate) | **OPEN** — the third P0; not started |

Safety of the deployed controller (INV-FEASIBLE, INV-NO-CYCLE, INV-BUDGET,
INV-TERMINATE) is separately machine-checked: Z3 P1–P9 (`verify_online_control.py`)
and the TLA+ spec (`AdaptiveReview.tla`).
