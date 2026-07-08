"""Property-based tests for the adaptive review controller (complements the Z3 proofs).

Z3 (scripts/verify_online_control.py) discharges the algebraic invariants; these
Hypothesis properties exercise the *whole* controller over thousands of random
DAGs, including the counting invariant (INV-TERMINATE) that is a loop argument
rather than an SMT obligation.
"""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from minimal_oversight.online_control import (
    ReleaseConfig, ReleaseState, Workflow, delivered_quality, online_step,
    online_step_release, optimal_allocation,
)

AGGS = ["product", "min", "mean"]


@st.composite
def workflows(draw):
    """A random DAG over a topological order 0..n-1 with random per-node params."""
    n = draw(st.integers(min_value=1, max_value=6))
    spec = []
    for i in range(n):
        parents = tuple(
            f"x{j}" for j in range(i)
            if draw(st.booleans())
        )
        agg = draw(st.sampled_from(AGGS)) if len(parents) > 1 else "product"
        c = draw(st.floats(min_value=0.3, max_value=0.95))
        f = draw(st.floats(min_value=0.5, max_value=1.0))
        spec.append((f"x{i}", c, parents, agg, f))
    return Workflow.build(spec)


@st.composite
def state(draw, wf):
    sigma = {v: draw(st.floats(min_value=0.05, max_value=0.95)) for v in wf.order}
    budget = {v: draw(st.floats(min_value=0.0, max_value=1.0)) for v in wf.order}
    return sigma, budget


@given(data=st.data())
@settings(max_examples=400)
def test_inv_budget_and_monotone(data):
    wf = data.draw(workflows())
    sigma, budget = data.draw(state(wf))
    p_min = data.draw(st.floats(min_value=0.0, max_value=1.0))
    delta, b_max = 0.05, 1.0
    q_before = delivered_quality(sigma, budget, wf)
    nxt = online_step(sigma, budget, wf, p_min, delta, b_max)
    # INV-BUDGET: every budget stays in [0, b_max]
    assert all(-1e-12 <= nxt[v] <= b_max + 1e-12 for v in wf.order)
    # INV-MONOTONE: a step never lowers delivered quality
    assert delivered_quality(sigma, nxt, wf) >= q_before - 1e-9


@given(data=st.data())
@settings(max_examples=200)
def test_inv_terminate(data):
    """With fixed state, repeated steps stop within n*ceil(b_max/delta) increments."""
    wf = data.draw(workflows())
    sigma, _ = data.draw(state(wf))
    delta, b_max, p_min = 0.05, 1.0, 0.99   # high target forces it to keep adding
    budget = {v: 0.0 for v in wf.order}
    bound = len(wf.order) * math.ceil(b_max / delta) + 2
    steps = 0
    while steps <= bound:
        nxt = online_step(sigma, budget, wf, p_min, delta, b_max)
        if nxt == budget:        # fixed point reached (no node helps / all capped)
            break
        budget = nxt
        steps += 1
    assert steps <= bound, f"did not terminate within {bound} steps"


@given(data=st.data())
@settings(max_examples=400)
def test_optimal_allocation_is_min_review_optimum(data):
    """The closed-form optimal_allocation is the per-step MSO optimum: it reaches the
    target whenever the target is achievable, spends review only on sinks, and no
    feasible allocation commits less total review. (This is the object the supplement
    bounds dynamic regret against; delivered_quality is separable across sinks and
    monotone, so the per-sink Euler-Lagrange thresholds are jointly optimal. The
    greedy re-solve used empirically only *approximates* this -- it can stall on tied
    bottleneck sinks -- which is why we report it as a heuristic, not the optimum.)
    """
    wf = data.draw(workflows())
    sigma = {v: data.draw(st.floats(min_value=0.05, max_value=0.95)) for v in wf.order}
    p_min = data.draw(st.floats(min_value=0.30, max_value=0.90))
    b_max = 1.0
    opt = optimal_allocation(sigma, wf, p_min, b_max)

    # feasible iff every sink can reach p_min within b_max
    def sink_reachable(s):
        if sigma[s] >= p_min:
            return True
        need = (p_min - sigma[s]) / ((1 - sigma[s]) * wf.catch[s] * wf.fix[s])
        return need <= b_max + 1e-12
    achievable = all(sink_reachable(s) for s in wf.sinks)
    opt_feasible = delivered_quality(sigma, opt, wf) >= p_min - 1e-9
    assert opt_feasible == achievable

    # only sinks receive review (interior budgets do not affect delivered quality)
    for v in wf.order:
        if v not in wf.sinks:
            assert opt[v] == 0.0

    # minimality: any feasible allocation commits at least as much review
    other = {v: data.draw(st.floats(min_value=0.0, max_value=1.0)) for v in wf.order}
    if delivered_quality(sigma, other, wf) >= p_min - 1e-9:
        assert sum(other.values()) >= sum(opt.values()) - 1e-9


# --------------------------------------------------------------------------- #
# Hysteresis-release controller: INV-BUDGET + INV-FEASIBLE + INV-TERMINATE     #
# (the release variant trades INV-MONOTONE for INV-FEASIBLE + INV-NO-CYCLE).   #
# --------------------------------------------------------------------------- #

@given(data=st.data())
@settings(max_examples=400)
def test_release_inv_budget_and_feasible(data):
    """One release step: stays in [0,b_max], keeps a feasible state feasible, and
    never lowers Q on the add path. Random dwell history exercises the release path."""
    wf = data.draw(workflows())
    sigma, budget = data.draw(state(wf))
    p_min = data.draw(st.floats(min_value=0.0, max_value=1.0))
    delta, b_max = 0.05, 1.0
    cfg = ReleaseConfig(
        margin=data.draw(st.floats(min_value=0.0, max_value=0.10)),
        deadband=data.draw(st.floats(min_value=0.0, max_value=0.10)),
        dwell=data.draw(st.integers(min_value=1, max_value=8)),
    )
    streak = {v: data.draw(st.integers(min_value=0, max_value=12)) for v in wf.order}
    nxt, _ = online_step_release(
        sigma, budget, wf, p_min, delta, ReleaseState(streak), cfg, b_max)
    # INV-BUDGET
    assert all(-1e-12 <= nxt[v] <= b_max + 1e-12 for v in wf.order)
    q_before = delivered_quality(sigma, budget, wf)
    q_after = delivered_quality(sigma, nxt, wf)
    if q_before >= p_min - 1e-12:
        assert q_after >= p_min - 1e-9          # INV-FEASIBLE: release never breaks it
    else:
        assert q_after >= q_before - 1e-9       # add path never lowers Q
    # at most one node changes per step (bounds switching; INV-TERMINATE counting)
    assert sum(abs(nxt[v] - budget[v]) > 1e-12 for v in wf.order) <= 1


@given(data=st.data())
@settings(max_examples=150)
def test_release_static_termination(data):
    """In a static feasible state the release controller reaches a fixed point (no
    add-then-release limit cycle: INV-NO-CYCLE / INV-TERMINATE for the variant)."""
    wf = data.draw(workflows())
    sigma = {v: data.draw(st.floats(min_value=0.6, max_value=0.95)) for v in wf.order}
    delta, b_max = 0.05, 1.0
    p_min = min(data.draw(st.floats(min_value=0.0, max_value=0.5)),
                min(sigma.values()) - 0.05)     # feasible even at zero budget
    cfg = ReleaseConfig(margin=0.03, deadband=0.04,            # margin+deadband>=delta
                        dwell=data.draw(st.integers(min_value=1, max_value=6)))
    budget = {v: b_max for v in wf.order}        # max slack -> releases must settle
    state_obj = ReleaseState.init(wf)
    bound = len(wf.order) * (math.ceil(b_max / delta) + cfg.dwell + 2) + 5
    unchanged, steps = 0, 0
    while steps <= bound:
        nxt, state_obj = online_step_release(
            sigma, budget, wf, p_min, delta, state_obj, cfg, b_max)
        assert all(-1e-12 <= nxt[v] <= b_max + 1e-12 for v in wf.order)   # INV-BUDGET
        assert delivered_quality(sigma, nxt, wf) >= p_min - 1e-9          # INV-FEASIBLE
        unchanged = unchanged + 1 if nxt == budget else 0
        budget = nxt
        steps += 1
        if unchanged > cfg.dwell:                # past any pending dwelled release
            break
    assert steps <= bound, f"release controller did not settle within {bound} steps"
