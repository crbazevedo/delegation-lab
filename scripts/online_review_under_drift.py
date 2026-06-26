#!/usr/bin/env python3
"""Online review allocation under competence drift.

The static results use the calibration operator's fixed point. This experiment
exercises the operator's *time dynamics* (Eq. 4): node skill drifts downward, the
operator carries raw competence toward the drifting skill at observation rate eta
(with decay delta), and review must be allocated *online* to hold delivered
quality at the target. We compare four runtime policies on a depth-3 chain:

  none          no review (b=0 throughout)
  fixed         a fixed uniform review budget set once at t=0
  online-unif   when Q_G < p_min, add a review increment spread over all nodes
  online-MSO    when Q_G < p_min, add the increment to the max-marginal node

Reported per policy: mean delivered quality, fraction of the run feasible, and
total review spent (area under the budget). The point: under drift, fixed review
decays through the target (a finite autonomy time), whereas online review holds
the target -- and the MSO marginal rule holds it with the least total review.
This positions MSO as an online (runtime) policy, not only an offline (design)
check. The eta sweep shows how observation frequency sets how fast the operator
senses drift.

Run:  PYTHONPATH=src python3 scripts/online_review_under_drift.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from minimal_oversight import _formulae as F  # noqa: E402

DEPTH = 3
SIGMA0_SKILL = 0.78        # starting per-node skill
CATCH = 0.70               # reviewer catch rate c (f=1)
P_MIN = 0.58               # delivered-quality target
DELTA_REVIEW = 0.05        # review increment added per intervention
B_MAX = 1.0                # per-node review cap
T = 300                    # timesteps
DT = 0.1
DRIFT = 0.010              # skill drift rate (per unit time)
DELTA_DECAY = 2.0          # operator evidence decay


def q_of(sigma_raw: np.ndarray, budgets: np.ndarray) -> tuple[float, np.ndarray]:
    """Sink delivered quality for a chain, given per-node raw competence + budget."""
    corr = np.zeros(DEPTH)
    for i in range(DEPTH):
        sr = sigma_raw[i]
        corr[i] = F.sigma_corr_fixed_point(sr, budgets[i] * CATCH, 1.0)
    return float(corr[-1]), corr


def run(policy: str, eta: float) -> dict:
    sigma_raw = np.full(DEPTH, SIGMA0_SKILL * eta / (eta + DELTA_DECAY))
    budgets = np.zeros(DEPTH)
    if policy == "fixed":
        budgets[:] = 0.5      # fixed uniform 0.5 per node (1.5 total) set once
    qs, feas, spend = [], 0, 0.0
    for t in range(T):
        skill = max(0.30, SIGMA0_SKILL - DRIFT * t * DT)
        # operator tracks drifting effective skill (chain: skill x upstream corr)
        _, corr_prev = q_of(sigma_raw, budgets)
        for i in range(DEPTH):
            up = corr_prev[i - 1] if i > 0 else 1.0
            skill_eff = skill * up
            sigma_raw[i] = F.calibration_operator_step(
                sigma_raw[i], skill_eff, eta, DELTA_DECAY, DT)
        qg, _ = q_of(sigma_raw, budgets)
        # online policies react to a shortfall
        if policy in ("online-unif", "online-mso") and qg < P_MIN:
            if policy == "online-unif":
                budgets = np.minimum(budgets + DELTA_REVIEW / DEPTH, B_MAX)
            else:  # online-mso: increment the node with the best marginal on Q_G
                best, best_gain = None, 0.0
                for i in range(DEPTH):
                    if budgets[i] + DELTA_REVIEW > B_MAX:
                        continue
                    trial = budgets.copy(); trial[i] += DELTA_REVIEW
                    gain = q_of(sigma_raw, trial)[0] - qg
                    if gain > best_gain:
                        best, best_gain = i, gain
                if best is not None:
                    budgets[best] = min(budgets[best] + DELTA_REVIEW, B_MAX)
        qg, _ = q_of(sigma_raw, budgets)
        qs.append(qg); feas += int(qg >= P_MIN); spend += budgets.sum() * DT
    return {"policy": policy, "eta": eta, "meanQ": float(np.mean(qs)),
            "feasible_frac": feas / T, "total_review": spend}


def main() -> int:
    for eta in (10.0,):
        print(f"=== Online review under drift (depth-{DEPTH} chain, drift={DRIFT}, "
              f"eta={eta}, p_min={P_MIN}) ===")
        print(f"{'policy':12s} {'meanQ':>7s} {'feasible%':>10s} {'total review':>13s}")
        for pol in ("none", "fixed", "online-unif", "online-mso"):
            r = run(pol, eta)
            print(f"{r['policy']:12s} {r['meanQ']:7.3f} {r['feasible_frac']*100:9.0f}% "
                  f"{r['total_review']:13.2f}")
    print("\n=== Observation-frequency (eta) sweep, online-MSO ===")
    print(f"{'eta':>5s} {'feasible%':>10s} {'total review':>13s}")
    for eta in (5.0, 10.0, 20.0):
        r = run("online-mso", eta)
        print(f"{eta:5.0f} {r['feasible_frac']*100:9.0f}% {r['total_review']:13.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
