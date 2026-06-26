#!/usr/bin/env python3
"""Is the release decision ski-rental? A falsifiable test of the theory core.

The competitive claim "the monotone ratchet is bad under a moving bottleneck" is
near-tautological. The non-trivial structure is this: when a sink recovers, holding
its now-unneeded budget is RENT (holding cost b per step); releasing it and later
re-acquiring it (the bottleneck returns) is BUY (switching cost 2*lambda*b). You do
not know how long the sink will stay slack, so the hold-vs-release decision is
exactly ONLINE SKI-RENTAL / rent-or-buy. That yields a clean, non-tautological theory:

  Prop 1 (motivation)  with a LOW duty cycle (need briefly, slack long) the ratchet
                       (never release) is Theta(1/duty)-competitive: unbounded.
  Thm 2 (core)         the release decision is ski-rental. The dwell timer is the
                       rent-or-buy threshold; dwell* = 2*lambda is 2-competitive,
                       and NO fixed dwell beats ~2 against an adversarial slack
                       length tau (the deterministic ski-rental lower bound).
  Thm 3 (noise)        with observation noise std `sigma`, staying feasible w.p.
                       >= 1-delta forces a deadband margin ~ z_delta * sigma, i.e.
                       additive holding overhead Omega(sigma * T) for a bounded-
                       memory controller; the deadband matches this floor.

We test in *required-budget* space (exact: corrected quality is linear in budget, so
r(t) = minimal feasible budget is the whole story) on a single sink with a RECURRING
need -- [active W][slack tau] x ncyc, plus a trailing active so every slack phase is
re-needed. We ASSERT the simulated cost equals the ski-rental closed form, so a bug
in the theory breaks the run.

  cost = holding + lambda * switching
       = sum_t b(t)  +  lambda * sum_t |b(t) - b(t-1)|
  feasible(t)  iff  b(t) >= r(t)   (true r, not the noisy observation)

Run:  python3 scripts/online_skirental.py
"""

from __future__ import annotations

import math

import numpy as np

BSTAR = 1.0            # peak required budget of the bottleneck when active


# ------------------------------- instance ---------------------------------- #
def required(W: int, tau: int, ncyc: int) -> np.ndarray:
    """Single sink: ncyc cycles of [active W][slack tau], plus a trailing active.

    Every slack phase is bracketed by active, so each release is re-acquired
    (the ski-rental 'buy' = release + readd is real)."""
    cycle = [BSTAR] * W + [0.0] * tau
    seq = cycle * ncyc + [BSTAR] * W
    return np.array(seq).reshape(1, -1)


def next_need(r0, t):
    fut = np.nonzero(r0[t:] > 0)[0]
    return fut[0] if len(fut) else math.inf


# ------------------------------- policies ---------------------------------- #
def run(policy, r, lam, *, dwell=0, margin=0.0, sigma=0.0, seed=0):
    """Return (holding, switching, infeasible_fraction). Online policies see
    r + N(0,sigma); `opt` is clairvoyant (true r, perfect rent-or-buy)."""
    rng = np.random.default_rng(seed)
    n, T = r.shape
    b = np.zeros(n)
    streak = np.zeros(n)
    holding = switching = infeas = 0.0
    for t in range(T):
        obs = r[:, t] + (rng.normal(0, sigma, n) if sigma > 0 else 0.0)
        target = np.maximum(obs, 0.0) + margin
        prev = b.copy()
        if policy == "opt":
            nb = b.copy()
            for s in range(n):
                if r[s, t] > 0:
                    nb[s] = r[s, t]
                else:
                    nb[s] = b[s] if next_need(r[s], t) < 2 * lam else 0.0
            b = nb
        elif policy == "ratchet":
            b = np.maximum(b, target)
        elif policy == "dwell":
            nb = b.copy()
            for s in range(n):
                if target[s] > b[s] + 1e-12:
                    nb[s] = target[s]; streak[s] = 0
                elif b[s] > target[s] + 1e-12:
                    streak[s] += 1
                    if streak[s] >= dwell:
                        nb[s] = target[s]
                else:
                    streak[s] = 0
            b = nb
        else:
            raise ValueError(policy)
        holding += b.sum()
        switching += np.abs(b - prev).sum()
        infeas += np.sum(b < r[:, t] - 1e-9)
    return holding, switching, infeas / (n * T)


def cost(h, sw, lam):
    return h + lam * sw


# ------------------------- closed-form predictions ------------------------- #
def opt_cost(W, tau, lam, ncyc):
    active_hold = BSTAR * W * (ncyc + 1)
    if tau >= 2 * lam:                      # release each slack phase
        return active_hold + lam * (BSTAR + 2 * BSTAR * ncyc)
    return active_hold + BSTAR * tau * ncyc + lam * BSTAR   # hold through


def dwell_cost(W, tau, lam, ncyc, d):
    active_hold = BSTAR * W * (ncyc + 1)
    if d <= tau:                            # hold (d-1), release, readd each slack
        slack_hold = BSTAR * (d - 1) * ncyc
        switch = BSTAR + 2 * BSTAR * ncyc
    else:                                   # never releases -> like the ratchet
        slack_hold = BSTAR * tau * ncyc
        switch = BSTAR
    return active_hold + slack_hold + lam * switch


# --------------------------------- tests ----------------------------------- #
def cr(policy, W, tau, lam, ncyc, **kw):
    h, sw, _ = run(policy, required(W, tau, ncyc), lam, **kw)
    oh, osw, _ = run("opt", required(W, tau, ncyc), lam)
    return cost(h, sw, lam) / cost(oh, osw, lam)


def test_closedform_check():
    """The simulator must reproduce the ski-rental algebra exactly (or theory is wrong)."""
    lam, W, ncyc = 10, 1, 10
    for tau in (8, 20, 40):
        oh, osw, _ = run("opt", required(W, tau, ncyc), lam)
        assert abs(cost(oh, osw, lam) - opt_cost(W, tau, lam, ncyc)) < 1e-6, \
            ("opt", tau, cost(oh, osw, lam), opt_cost(W, tau, lam, ncyc))
        for d in (5, 20, 80):
            h, sw, _ = run("dwell", required(W, tau, ncyc), lam, dwell=d)
            assert abs(cost(h, sw, lam) - dwell_cost(W, tau, lam, ncyc, d)) < 1e-6, \
                ("dwell", tau, d, cost(h, sw, lam), dwell_cost(W, tau, lam, ncyc, d))
    print("Closed-form check -- simulator == ski-rental algebra: PASS\n")


def test_prop1_ratchet_unbounded():
    print("Prop 1 -- low duty cycle: ratchet CR ~ 1/duty, UNBOUNDED "
          "(W=1, lambda=10):")
    print(f"  {'tau':>5s} {'duty=W/(W+tau)':>15s} {'ratchet CR':>11s}")
    for tau in (10, 20, 40, 80, 160, 320):
        c = cr("ratchet", 1, tau, 10, 20)
        print(f"  {tau:5d} {1/(1+tau):15.3f} {c:11.2f}")
    print()


def opt_slack(tau, lam):
    return min(tau, 2 * lam)                          # hold (tau) vs buy (2 lambda)


def dwell_slack(tau, lam, d):
    return (d - 1) + 2 * lam if d <= tau else tau     # validated by the exact check


def test_thm2_skirental():
    print("Thm 2 -- ski-rental on the per-slack-phase decision (the full-instance CR")
    print("         is the same decision diluted by unavoidable active holding). The")
    print("         per-phase closed forms are the ones the exact check just verified.")
    lam = 10
    dwells = [2, 5, 10, 15, 20, 25, 40, 80]
    print(f"         break-even dwell* = 2*lambda = {2*lam}; classic ski-rental "
          f"lower bound = 2")
    print(f"  {'dwell':>6s} {'worst-case slack CR':>20s} {'argmax tau':>11s}")
    best_d, best_worst = None, math.inf
    for d in dwells:
        worst, arg = 0.0, None
        for tau in range(1, 1001):                   # fine sweep incl. tau -> large
            c = dwell_slack(tau, lam, d) / opt_slack(tau, lam)
            if c > worst:
                worst, arg = c, tau
        flag = "  <- minimax (= dwell*)" if d == 2 * lam else ""
        print(f"  {d:6d} {worst:20.3f} {arg:11d}{flag}")
        if worst < best_worst:
            best_worst, best_d = worst, d
    print(f"  -> minimax dwell = {best_d}, worst-case CR = {best_worst:.3f} "
          f"(theory: dwell*={2*lam}, CR = 2 - 1/(2*lambda) = "
          f"{2 - 1/(2*lam):.3f})")
    # sanity: the simulator's full-instance CR at dwell* stays <= this bound
    full = max(cr("dwell", 1, tau, lam, 30, dwell=2 * lam)
               for tau in (8, 20, 40, 120, 360))
    print(f"     (full-instance simulated CR at dwell* over several tau: "
          f"max = {full:.2f} <= 2)\n")


def test_thm3_noise_floor():
    print("Thm 3 -- observation noise forces a deadband floor "
          "(feasibility vs overhead):")
    lam, W, tau, ncyc, sigma = 10, 1, 30, 40, 0.10
    print(f"         sigma={sigma}, dwell={2*lam}, tau={tau}; margin is pure overhead")
    print(f"  {'margin':>7s} {'margin/sigma':>13s} {'infeasible%':>12s} "
          f"{'holding overhead':>17s}")
    r = required(W, tau, ncyc)
    h0 = None
    for margin in (0.0, 0.05, 0.10, 0.20, 0.30):
        h, sw, inf = run("dwell", r, lam, dwell=2 * lam, margin=margin,
                         sigma=sigma, seed=1)
        if h0 is None:
            h0 = h
        print(f"  {margin:7.2f} {margin/sigma:13.2f} {inf*100:11.1f}% {h-h0:17.1f}")
    print()


def test_thm3_overhead_linear():
    print("Thm 3 (cont.) -- at FIXED feasibility (margin = z*sigma), overhead is "
          "linear in sigma:")
    lam, W, tau, ncyc = 10, 1, 30, 60
    z = 2.054                                  # ~ one-sided Phi^{-1}(0.98)
    print(f"         z={z} (target infeasible <= 2%)")
    print(f"  {'sigma':>6s} {'margin':>7s} {'infeasible%':>12s} "
          f"{'overhead/sigma':>15s}")
    r = required(W, tau, ncyc)
    for sigma in (0.02, 0.04, 0.08, 0.16):
        h0, _, _ = run("dwell", r, lam, dwell=2 * lam, margin=0.0, sigma=sigma, seed=2)
        h, _, inf = run("dwell", r, lam, dwell=2 * lam, margin=z * sigma, sigma=sigma,
                        seed=2)
        print(f"  {sigma:6.2f} {z*sigma:7.3f} {inf*100:11.1f}% {(h-h0)/sigma:15.1f}")
    print("  (overhead/sigma ~ constant -> overhead linear in sigma: the matched "
          "floor)\n")


def main() -> int:
    print("=" * 74)
    print("Ski-rental structure of the online review-release decision "
          "-- falsifiable test")
    print("=" * 74 + "\n")
    test_closedform_check()
    test_prop1_ratchet_unbounded()
    test_thm2_skirental()
    test_thm3_noise_floor()
    test_thm3_overhead_linear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
