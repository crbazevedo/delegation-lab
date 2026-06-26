"""Online MSO review controller -- the runtime allocation policy.

This is the algorithm behind the paper's online result. A workflow runs under
competence drift; the calibration operator carries each node's raw competence
toward its (drifting) skill; at each control step the controller observes
delivered quality and, only when it dips below target, adds one review increment
to the node with the largest marginal effect on delivered quality.

Algorithm (one control step; ``sigma_raw`` is the operator's current state):
    1. Q <- delivered_quality(sigma_raw, budget)        # bottleneck sink quality
    2. if Q >= p_min: return budget                      # no review added
    3. v* <- argmax_v { delivered_quality(sigma_raw, budget + delta*e_v) - Q
                        : budget[v] + delta <= b_max }   # MSO marginal rule
    4. if v* exists and the gain is positive: budget[v*] += delta
    5. return budget

Invariants (machine-checked --- Z3: ``scripts/verify_online_control.py``;
property tests: ``tests/test_online_control.py``; TLA+ spec: ``formal/OnlineMSO.tla``):

    INV-BUDGET     every budget[v] stays in [0, b_max], so the policy never
                   over-commits review.
    INV-MONOTONE   delivered_quality is non-decreasing in each budget[v]
                   (corrected quality is monotone in b, and product/min/mean
                   aggregations are monotone), so a control step never lowers Q.
    INV-TERMINATE  a step adds at most ``delta`` to one node and total budget is
                   bounded by n*b_max, so at most ceil(n*b_max/delta) increments
                   ever fire; the step itself is O(n) marginal evaluations.

The marginal in step 3 is myopic (one-step): it values a node by its immediate
effect on the bottleneck sink. Upstream review still pays off through the operator
dynamics over subsequent steps; a propagation-aware (lookahead) marginal is left
to future work.

Why a release variant (``online_step_release``).  ``online_step`` is a *monotone
ratchet*: INV-MONOTONE says it only ever ADDS budget. Under competence drift with a
*single* bottleneck that degrades monotonically, that is exactly right and the
ratchet is competitive against the dynamic (per-step) optimum. But under
*alternating-bottleneck* drift -- two or more sinks that take turns being the
weakest link -- the ratchet piles budget on every sink that was ever a contender
and never frees it, so its committed review (the holding cost) grows without bound
relative to the dynamic optimum, which sheds budget from a recovered sink. A
competitive-analysis study (``scripts/online_competitive.py``) measures this gap.

``online_step_release`` adds an OPTIONAL hysteresis-guarded release. It is NOT the
naive "release whatever is slack every step" rule -- that churns, paying repeated
switching cost as a sink crosses the target back and forth. Release is gated by a
DEADBAND (a sink must be slack beyond ``p_min + margin + deadband`` to arm) and a
DWELL timer (it must stay armed for ``dwell`` consecutive steps), and the released
sink is provably kept feasible. This trades INV-MONOTONE (which no longer holds --
a release lowers Q on purpose) for two weaker machine-checked properties:

    INV-FEASIBLE   a release from a feasible state keeps delivered_quality >= p_min
                   (the post-release guard ``corrected(s, b_s - delta) >= p_min +
                   margin``; Z3 P8). The ratchet's INV-MONOTONE is the special case
                   margin -> infinity (never release).
    INV-NO-CYCLE   the add region (Q < p_min) and the release/arm region are
                   separated by the deadband, so in a static state the controller
                   cannot add-then-release the same sink forever -- a Lyapunov
                   argument (committed review on a slack sink strictly decreases
                   until it rests inside the deadband) that, with INV-BUDGET, keeps
                   INV-TERMINATE (Z3 P9; static-state termination test).

INV-BUDGET and INV-TERMINATE hold for BOTH controllers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Workflow:
    """An immutable workflow over a fixed topological order.

    nodes: id -> (catch_rate c in [0,1], parents tuple, aggregation, fix_rate f).
    """

    catch: dict[str, float]
    parents: dict[str, tuple]
    agg: dict[str, str]
    order: tuple
    sinks: tuple
    fix: dict[str, float]

    @staticmethod
    def build(spec: list[tuple]) -> "Workflow":
        """spec: list of (id, catch, parents, aggregation[, fix])."""
        catch, parents, agg, fix = {}, {}, {}, {}
        for row in spec:
            nid, c, ps, a = row[0], row[1], tuple(row[2]), row[3]
            f = row[4] if len(row) > 4 else 1.0
            catch[nid], parents[nid], agg[nid], fix[nid] = c, ps, a, f
        order = tuple(nid for nid, *_ in spec)
        children = {nid: 0 for nid in order}
        for nid in order:
            for p in parents[nid]:
                children[p] += 1
        sinks = tuple(nid for nid in order if children[nid] == 0)
        return Workflow(catch, parents, agg, order, sinks, fix)


def corrected(sigma_raw_v: float, b_v: float, c_v: float, f_v: float) -> float:
    """Corrected quality at a node: sigma_corr = sigma_raw + (1-sigma_raw)*b*c*f.

    Monotone non-decreasing in b_v on [0,1] (INV-MONOTONE, per node).
    """
    return sigma_raw_v + (1.0 - sigma_raw_v) * b_v * c_v * f_v


def delivered_quality(sigma_raw: dict[str, float], budget: dict[str, float],
                      wf: Workflow) -> float:
    """Bottleneck (minimum-sink) delivered quality given the operator state."""
    corr = {v: corrected(sigma_raw[v], budget[v], wf.catch[v], wf.fix[v])
            for v in wf.order}
    return min(corr[s] for s in wf.sinks)


def marginal_node(sigma_raw: dict[str, float], budget: dict[str, float],
                  wf: Workflow, delta: float, b_max: float):
    """The node with the largest positive marginal gain on Q, or None."""
    base = delivered_quality(sigma_raw, budget, wf)
    best, best_gain = None, 0.0
    for v in wf.order:
        if budget[v] + delta > b_max + 1e-12:
            continue
        trial = dict(budget)
        trial[v] = budget[v] + delta
        gain = delivered_quality(sigma_raw, trial, wf) - base
        if gain > best_gain + 1e-15:
            best, best_gain = v, gain
    return best


def optimal_allocation(sigma_raw: dict[str, float], wf: Workflow,
                       p_min: float, b_max: float = 1.0) -> dict[str, float]:
    """Per-step MSO optimum, in closed form (NOT a greedy search).

    ``delivered_quality`` is the minimum over sinks of ``corrected``, which is
    *linear and increasing* in each sink's budget and independent of interior
    budgets. The minimum-review allocation that reaches ``p_min`` therefore sets
    every interior node to zero and each sink to its Euler-Lagrange threshold
    (the corrector-capacity bound, ``_formulae.corrector_capacity_threshold``):

        b*(s) = clip( (p_min - sigma_raw[s]) / [(1 - sigma_raw[s]) c_s f_s], 0, b_max ).

    This is the exact per-step optimum for the separable max-min objective: it is
    feasible whenever *any* allocation is, and uses the least review to be so.
    It is used as the receding-horizon (MPC) comparator and is computed without
    calling ``online_step`` / ``marginal_node``, so it is an independent oracle.
    """
    b = {v: 0.0 for v in wf.order}
    for s in wf.sinks:
        sr = sigma_raw[s]
        c_eff = wf.catch[s] * wf.fix[s]
        if p_min <= sr:
            need = 0.0
        elif c_eff <= 0.0 or (1.0 - sr) <= 0.0:
            need = b_max          # sink cannot reach p_min; cap (infeasible)
        else:
            need = (p_min - sr) / ((1.0 - sr) * c_eff)
        b[s] = min(max(0.0, need), b_max)
    return b


def online_step(sigma_raw: dict[str, float], budget: dict[str, float],
                wf: Workflow, p_min: float, delta: float,
                b_max: float = 1.0) -> dict[str, float]:
    """One control step. Returns a NEW budget dict (input is not mutated).

    Postconditions (INV-BUDGET, INV-MONOTONE): every value stays in [0, b_max],
    and delivered_quality(new_budget) >= delivered_quality(old_budget).
    """
    if delivered_quality(sigma_raw, budget, wf) >= p_min:
        return dict(budget)
    v = marginal_node(sigma_raw, budget, wf, delta, b_max)
    out = dict(budget)
    if v is not None:
        out[v] = min(budget[v] + delta, b_max)
    return out


# --------------------------------------------------------------------------- #
# Optional hysteresis-release variant (tracks an alternating bottleneck).      #
# See the module docstring: trades INV-MONOTONE for INV-FEASIBLE + INV-NO-CYCLE.#
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ReleaseConfig:
    """Knobs for the hysteresis-guarded release in ``online_step_release``.

    margin   post-release safety floor: a sink is released only if its corrected
             quality would stay >= p_min + margin, so a release never breaks
             feasibility (INV-FEASIBLE). margin -> inf recovers the ratchet.
    deadband extra slack a sink must currently exceed (corrected >= p_min +
             margin + deadband) before it even arms its dwell clock. Separates the
             add region from the release region so the controller cannot oscillate
             around the target (INV-NO-CYCLE). Choose margin + deadband >= one grid
             step (max-gain * delta) to forbid an add-then-release limit cycle.
    dwell    number of consecutive armed steps required before a release fires, so
             a momentary demand dip does not trigger a release (anti-churn in time).
    """

    margin: float = 0.03
    deadband: float = 0.03
    dwell: int = 5


@dataclass(frozen=True)
class ReleaseState:
    """Per-node dwell counters carried between ``online_step_release`` calls.

    ``slack_streak[v]`` is the number of consecutive steps node ``v`` has been
    armed for release (slack beyond the deadband). It is immutable; each step
    returns a fresh state, mirroring the budget dict.
    """

    slack_streak: dict[str, int]

    @staticmethod
    def init(wf: Workflow) -> "ReleaseState":
        return ReleaseState({v: 0 for v in wf.order})


def online_step_release(sigma_raw: dict[str, float], budget: dict[str, float],
                        wf: Workflow, p_min: float, delta: float,
                        state: ReleaseState, cfg: ReleaseConfig,
                        b_max: float = 1.0) -> tuple[dict[str, float], ReleaseState]:
    """One control step of the hysteresis-release controller.

    Returns ``(new_budget, new_state)`` (neither input is mutated). Unlike
    ``online_step`` (a monotone ratchet that only adds), this MAY release one
    increment from a persistently-slack sink, so committed review tracks an
    alternating bottleneck instead of accumulating on every contender.

    One node changes per step at most (ADD when Q < p_min, else at most one
    RELEASE), which bounds switching cost and preserves the INV-TERMINATE
    counting argument. Postconditions:

      * INV-BUDGET   every value stays in [0, b_max].
      * INV-FEASIBLE if Q(budget) >= p_min then Q(new_budget) >= p_min: an ADD
                     cannot lower Q (INV-MONOTONE on the add path), and a RELEASE
                     fires only behind the post-release guard
                     ``corrected(s, b_s - delta) >= p_min + margin`` (Z3 P8).
    """
    out = dict(budget)
    if delivered_quality(sigma_raw, budget, wf) < p_min:
        # Deficit: ADD exactly as the ratchet does, and disarm every node --
        # nothing is slack while we are below target.
        v = marginal_node(sigma_raw, budget, wf, delta, b_max)
        if v is not None:
            out[v] = min(budget[v] + delta, b_max)
        return out, ReleaseState.init(wf)

    # Feasible: consider releasing from a persistently-slack sink. Interior nodes
    # never carry budget (they do not affect delivered_quality), so only sinks
    # arm the dwell clock; everything else stays disarmed.
    #
    # arm_level sits a full deadband above the margin floor. A sink sheds one
    # increment per step WHILE it stays armed (corrected >= arm_level), so it
    # tracks a recovered bottleneck quickly; it stops on its own once corrected
    # falls into the deadband [p_min + margin, arm_level), never overshooting
    # below p_min (the floor is the anti-churn guarantee, not the dwell). The
    # dwell only gates the ONSET of shedding, so a slack blip shorter than
    # ``dwell`` steps never triggers a release.
    arm_level = p_min + cfg.margin + cfg.deadband
    streak = {v: 0 for v in wf.order}
    best_s, best_slack = None, 0.0
    for s in wf.sinks:
        c_s = corrected(sigma_raw[s], budget[s], wf.catch[s], wf.fix[s])
        armed = budget[s] >= delta - 1e-12 and c_s >= arm_level - 1e-12
        streak[s] = state.slack_streak.get(s, 0) + 1 if armed else 0
        if streak[s] < cfg.dwell:
            continue
        post = corrected(sigma_raw[s], budget[s] - delta, wf.catch[s], wf.fix[s])
        if post < p_min + cfg.margin - 1e-12:        # INV-FEASIBLE guard
            continue
        slack = c_s - (p_min + cfg.margin)           # release the most-slack sink
        if slack > best_slack + 1e-15:
            best_s, best_slack = s, slack

    if best_s is not None:
        out[best_s] = max(budget[best_s] - delta, 0.0)
        # streak is NOT reset: a still-armed sink keeps shedding next step until
        # it settles into the deadband, so recovery is not throttled to one
        # increment per ``dwell`` steps.
    return out, ReleaseState(streak)
