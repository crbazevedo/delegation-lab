#!/usr/bin/env python3
"""Competitive analysis of the online review controllers under two drift families.

This operationalises the T2 finding in-repo. The adaptive controller in
``minimal_oversight/online_control.py`` is judged against the *dynamic* (per-step)
optimum: the GRID-snapped ``optimal_allocation`` -- the release-capable oracle that
re-solves the minimal feasible allocation every step, rounded to the same delta
lattice the online policies move on (so switching is compared like-for-like). We
measure the COMPETITIVE RATIO (policy cost / dynamic-OPT cost) on two families:

  monotone     a single sink degrades monotonically; the bottleneck never moves.
               Here the ratchet is competitive -- it only ever needs to add.
  alternating  k sinks dip out of phase (a moving bottleneck). Here the monotone
               ratchet is NOT competitive: it holds peak budget on EVERY sink that
               was ever a contender; OPT sheds a recovered sink each phase. As the
               dip duty cycle falls, the ratchet's holding over OPT grows ~1/duty.

The dip is prescribed in BUDGET space as a trapezoid whose required budget ramps
at exactly delta/step, so every policy CAN track it (a feasible-by-slew dip). That
isolates the holding/switching question from a slew-rate limit -- on a faster dip
than delta/step, releasing is dangerous (you cannot re-acquire in time) and the
ratchet's never-released budget is feasibility insurance; feasible% surfaces that.

Cost model (a metrical-task-system flavour). Reconfiguring review is a DISCRETE
action (re-tasking a reviewer), so switching is counted per event, not per unit:

    holding = sum_t sum_v b_v(t)                       # rent: committed review
    events  = sum_t sum_v [ b_v(t) != b_v(t-1) ]       # # of budget changes
    cost    = holding + LAMBDA * events
    CR(policy) = cost(policy) / cost(dynamic-OPT)

Policies (all online; OPT alone is the offline oracle):
  ratchet      online_step                 -- add-only (INV-MONOTONE). Over-holds.
  naive        un-guarded every-step release: when feasible, drop delta from the
               most-slack sink with NO post-release check -- overshoots and re-adds
               (churns; dips infeasible). The straw man the margin fixes.
  guarded      online_step_release, margin only (deadband=0, dwell=1) -- post-release
               feasibility checked, but no deadband/dwell.
  hysteresis   online_step_release, full deadband + dwell.
  dynamic-OPT  grid-snapped optimal_allocation -- per-step releasing optimum.

Run:  PYTHONPATH=src python3 scripts/online_competitive.py
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from minimal_oversight.online_control import (  # noqa: E402
    ReleaseConfig, ReleaseState, Workflow, corrected, delivered_quality,
    marginal_node, online_step, online_step_release, optimal_allocation,
)

# ------------------------------- parameters -------------------------------- #
P_MIN = 0.58           # delivered-quality target
DELTA = 0.05           # review increment (grid step)
B_MAX = 1.0            # per-sink review cap
CATCH = 0.70           # reviewer catch rate (fix = 1)
T = 1200               # control steps
LAMBDA = 1.0           # per-event switching weight (sensitivity reported below)
DEPTH_B = 0.65         # peak review a dipping sink needs (sets dip depth)
PERIOD = 200           # alternating dip period
DWELL_AT_DEPTH = 16    # steps a dipping sink sits at full depth
NOISE = 0.03           # std of the controller's per-step skill OBSERVATION noise
SEED = 7               # noise seed (same sequence across policies -> paired design)

GUARDED = ReleaseConfig(margin=0.03, deadband=0.0, dwell=1)    # margin only
HYSTERESIS = ReleaseConfig(margin=0.03, deadband=0.04, dwell=6)


def sinks_wf(k: int) -> Workflow:
    """k independent single-node sinks (delivered_quality = min over sinks)."""
    return Workflow.build([(f"s{i}", CATCH, (), "product") for i in range(k)])


def sigma_for_need(r: float) -> float:
    """Skill whose minimal feasible budget is exactly r (inverse of the need rule).

    need(sigma) = (p_min - sigma) / ((1 - sigma) c);  invert for sigma given r.
    r <= 0 maps to sigma = p_min (a recovered sink: zero budget needed, and any
    budget it still holds is pure slack -- which is what the ratchet wastes).
    """
    if r <= 0.0:
        return P_MIN
    rc = r * CATCH
    return (P_MIN - rc) / (1.0 - rc)


def grid_opt(sigma_raw, wf) -> dict[str, float]:
    """Dynamic OPT snapped UP to the delta grid (the discrete releasing optimum)."""
    cont = optimal_allocation(sigma_raw, wf, P_MIN, B_MAX)
    out = {}
    for v in wf.order:
        steps = math.ceil(cont[v] / DELTA - 1e-9)
        out[v] = min(steps * DELTA, B_MAX)
    return out


# --------------------------------- drift ----------------------------------- #
def _need_of_linear_skill(frac: float) -> float:
    sigma = 0.92 + (0.20 - 0.92) * frac
    if sigma >= P_MIN:
        return 0.0
    return (P_MIN - sigma) / ((1 - sigma) * CATCH)


def sigma_monotone(t: int, k: int) -> dict[str, float]:
    """Sink s0's skill degrades linearly 0.92->0.20; the rest stay high.

    A single, never-moving bottleneck -- the ratchet's competitive regime.
    """
    sig = {f"s{i}": 0.92 for i in range(k)}
    sig["s0"] = sigma_for_need(_need_of_linear_skill(t / (T - 1)))
    return sig


def _trapezoid_need(phase: int) -> float:
    """Required budget over one dip: ramp up at delta/step, dwell, ramp down."""
    ramp = max(1, math.ceil(DEPTH_B / DELTA))     # steps to reach depth at delta/step
    if phase < ramp:
        return DELTA * (phase + 1)
    if phase < ramp + DWELL_AT_DEPTH:
        return DEPTH_B
    if phase < 2 * ramp + DWELL_AT_DEPTH:
        return max(0.0, DEPTH_B - DELTA * (phase - ramp - DWELL_AT_DEPTH + 1))
    return 0.0


def sigma_alternating(t: int, k: int, period: int = PERIOD) -> dict[str, float]:
    """Each sink dips (need 0 -> DEPTH_B -> 0) once per period, phases spread evenly.

    Prescribed in budget space so the requirement ramps at delta/step (trackable).
    The recovered plateau (need 0, sigma = p_min) is where a sink that still holds
    budget is pure slack -- the ratchet never sheds it, OPT/release do.
    """
    sig = {}
    for i in range(k):
        phase = (t + i * period // k) % period
        sig[f"s{i}"] = sigma_for_need(_trapezoid_need(phase))
    return sig


# ------------------------------- policies ---------------------------------- #
def naive_release_step(sigma_raw, budget, wf, p_min, delta, b_max):
    """Add when short; else drop delta from the most-slack sink with NO post-check."""
    if delivered_quality(sigma_raw, budget, wf) < p_min:
        v = marginal_node(sigma_raw, budget, wf, delta, b_max)
        out = dict(budget)
        if v is not None:
            out[v] = min(budget[v] + delta, b_max)
        return out
    best_s, best_c = None, p_min
    for s in wf.sinks:
        if budget[s] < delta - 1e-12:
            continue
        c_s = corrected(sigma_raw[s], budget[s], wf.catch[s], wf.fix[s])
        if c_s > best_c + 1e-15:           # currently slack -- release optimistically
            best_s, best_c = s, c_s
    out = dict(budget)
    if best_s is not None:
        out[best_s] = budget[best_s] - delta
    return out


def run_policy(policy: str, drift, wf: Workflow, k: int, cfg: ReleaseConfig,
               noise: float, seed: int):
    """Return (holding, events, feasible_fraction) for one policy over T steps.

    Online policies act on a NOISY observation of the skill; OPT is the offline
    oracle and acts on the true skill. Holding/events are measured on the actual
    budget; feasibility is measured against the TRUE delivered quality. The noise
    sequence is seed-fixed, so every policy sees the same draws (paired design).
    """
    rng = np.random.default_rng(seed)
    budget = {v: 0.0 for v in wf.order}
    state = ReleaseState.init(wf)
    holding = events = feas = 0.0
    for t in range(T):
        sigma = drift(t, k)
        obs = sigma if noise <= 0 else {
            v: float(np.clip(sigma[v] + rng.normal(0.0, noise), 1e-3, 1 - 1e-3))
            for v in wf.order}
        prev = budget
        if policy == "ratchet":
            budget = online_step(obs, budget, wf, P_MIN, DELTA, B_MAX)
        elif policy == "naive":
            budget = naive_release_step(obs, budget, wf, P_MIN, DELTA, B_MAX)
        elif policy in ("guarded", "hysteresis"):
            budget, state = online_step_release(
                obs, budget, wf, P_MIN, DELTA, state, cfg, B_MAX)
        elif policy == "opt":
            budget = grid_opt(sigma, wf)        # oracle: true skill
        else:
            raise ValueError(policy)
        holding += sum(budget.values())
        events += sum(abs(budget[v] - prev[v]) > 1e-12 for v in wf.order)
        feas += int(delivered_quality(sigma, budget, wf) >= P_MIN - 1e-9)
    return holding, events, feas / T


POLICIES = {"ratchet": None, "naive": None,
            "guarded": GUARDED, "hysteresis": HYSTERESIS, "opt": None}


@dataclass
class Row:
    family: str
    policy: str
    holding: float
    events: float
    cost: float
    cr: float
    feasible: float


def evaluate(k: int = 2, lam: float = LAMBDA, period: int = PERIOD,
             noise: float = NOISE) -> list[Row]:
    rows: list[Row] = []
    wf = sinks_wf(k)
    drifts = {"monotone": sigma_monotone,
              "alternating": lambda t, kk: sigma_alternating(t, kk, period)}
    for fam, drift in drifts.items():
        raw, cost = {}, {}
        for pol, cfg in POLICIES.items():
            h, ev, fe = run_policy(pol, drift, wf, k, cfg or HYSTERESIS, noise, SEED)
            raw[pol] = (h, ev, fe)
            cost[pol] = h + lam * ev
        for pol in ("ratchet", "naive", "guarded", "hysteresis", "opt"):
            h, ev, fe = raw[pol]
            rows.append(Row(fam, pol, h, ev, cost[pol],
                            cost[pol] / cost["opt"], fe))
    return rows


def print_table(rows: list[Row]):
    print(f"{'family':12s} {'policy':11s} {'holding':>9s} {'events':>8s} "
          f"{'cost':>9s} {'CR':>7s} {'feasible%':>10s}")
    print("-" * 74)
    last = None
    for r in rows:
        if last is not None and r.family != last:
            print()
        note = ""
        if r.family == "alternating" and r.policy == "ratchet" and r.cr > 3:
            note = "  <- over-holds"
        if r.policy == "naive" and r.feasible < 0.985:
            note = "  <- churns/infeasible"
        print(f"{r.family:12s} {r.policy:11s} {r.holding:9.1f} {r.events:8.0f} "
              f"{r.cost:9.1f} {r.cr:7.2f} {r.feasible*100:9.0f}%{note}")
        last = r.family


def main() -> int:
    print(f"=== Competitive ratio vs dynamic OPT (k=2, lambda={LAMBDA}, T={T}, "
          f"period={PERIOD}) ===\n")
    print_table(evaluate())

    print("\n=== Alternating: ratchet CR vs dip period (longer period = lower duty "
          "= ratchet holds longer) ===")
    print(f"{'period':>7s} {'duty':>6s} {'ratchet':>8s} {'naive':>7s} "
          f"{'guard':>7s} {'hyst':>7s} {'hyst feas%':>11s}")
    dip_len = 2 * max(1, math.ceil(DEPTH_B / DELTA)) + DWELL_AT_DEPTH
    for period in (90, 140, 200, 320, 480):
        d = {r.policy: r for r in evaluate(period=period) if r.family == "alternating"}
        print(f"{period:7d} {dip_len/period:6.2f} {d['ratchet'].cr:8.2f} "
              f"{d['naive'].cr:7.2f} {d['guarded'].cr:7.2f} {d['hysteresis'].cr:7.2f} "
              f"{d['hysteresis'].feasible*100:10.0f}%")

    print("\n=== Alternating: CR vs #contended sinks k (ratchet holds them ALL) ===")
    print(f"{'k':>3s} {'ratchet':>8s} {'naive':>7s} {'guard':>7s} {'hyst':>7s}")
    for k in (2, 3, 4, 6):
        d = {r.policy: r for r in evaluate(k=k) if r.family == "alternating"}
        print(f"{k:3d} {d['ratchet'].cr:8.2f} {d['naive'].cr:7.2f} "
              f"{d['guarded'].cr:7.2f} {d['hysteresis'].cr:7.2f}")

    print("\n=== Switching-weight (lambda) sensitivity, alternating, k=2 ===")
    print(f"{'lambda':>7s} {'ratchet':>8s} {'naive':>7s} {'guard':>7s} {'hyst':>7s}")
    for lam in (0.0, 0.5, 1.0, 3.0):
        d = {r.policy: r for r in evaluate(lam=lam) if r.family == "alternating"}
        print(f"{lam:7.1f} {d['ratchet'].cr:8.2f} {d['naive'].cr:7.2f} "
              f"{d['guarded'].cr:7.2f} {d['hysteresis'].cr:7.2f}")

    print("\n=== Observation-noise sensitivity, alternating, k=2 "
          "(CR | feasible%) -- noise is what the deadband+dwell reject ===")
    print(f"{'noise':>6s} | {'ratchet':>13s} | {'naive':>13s} | {'guarded':>13s} "
          f"| {'hyst':>13s}")
    for noise in (0.0, 0.02, 0.04, 0.06):
        d = {r.policy: r for r in evaluate(noise=noise) if r.family == "alternating"}
        cells = " | ".join(
            f"{d[p].cr:5.2f} {d[p].feasible*100:4.0f}%"
            for p in ("ratchet", "naive", "guarded", "hysteresis"))
        print(f"{noise:6.2f} | {cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
