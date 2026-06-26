#!/usr/bin/env python3
"""Online review under drift across the testbed: paired treatment effects + motif
heterogeneity.

The single-workflow run (online_review_under_drift.py) is generalized here to the
whole topology testbed, with per-node parameter dispersion (heterogeneous graphs).

Causal design. The simulation gives exact counterfactuals: the same workflow under
the same drift realization is run under each policy, so policy is an intervention
with no confounding (the paired re-run is the do-operator). We therefore report the
*average treatment effect* (ATE) of online-MSO over baselines as a paired mean with
a 95% CI -- no propensity/IV adjustment is needed or appropriate. We then study
*effect heterogeneity*: each workflow carries motif features (chain depth, max
merge fan-in, presence of a weakest-link min gate, node count, sink catch rate),
and we regress the per-workflow effect on those features (OLS) to estimate each
feature's contribution to the policy's benefit.

Run:  PYTHONPATH=src python3 scripts/online_testbed.py
"""

from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from minimal_oversight import _formulae as F  # noqa: E402

CATCH0, MU, DELTA_DECAY = 0.70, 0.010, 2.0
P_MIN, T, DT = 0.58, 200, 0.1
DREVIEW, BMAX = 0.05, 1.0
ETA = 10.0
GAMMA_MAB, C_MAB = 0.95, 0.4  # discounted-UCB: drift discount + exploration coef

# Each topology: list of (id, parents, aggregation). Heterogeneous params drawn per seed.
TOPOS = {
    "chain2":  [("n0", (), "product"), ("n1", ("n0",), "product")],
    "chain3":  [("n0", (), "product"), ("n1", ("n0",), "product"), ("n2", ("n1",), "product")],
    "chain4":  [("n0", (), "product"), ("n1", ("n0",), "product"), ("n2", ("n1",), "product"), ("n3", ("n2",), "product")],
    "merge2":  [("p0", (), "product"), ("p1", (), "product"), ("m", ("p0", "p1"), "product")],
    "merge3":  [("p0", (), "product"), ("p1", (), "product"), ("p2", (), "product"), ("m", ("p0", "p1", "p2"), "product")],
    "diamond": [("s", (), "product"), ("a", ("s",), "product"), ("b", ("s",), "product"), ("m", ("a", "b"), "product")],
    "fanout":  [("s", (), "product"), ("x0", ("s",), "product"), ("x1", ("s",), "product"), ("x2", ("s",), "product"), ("m", ("x0", "x1", "x2"), "mean")],
    "mixed":   [("d", (), "product"), ("r0", ("d",), "mean"), ("r1", ("d",), "mean"),
                ("rv", ("r0", "r1"), "mean"), ("g", ("rv",), "min"), ("mg", ("g",), "mean")],
}


def features(topo: str) -> dict:
    spec = TOPOS[topo]
    parents = {nid: ps for nid, ps, _ in spec}
    # longest path (depth) via memo over the DAG
    order = [nid for nid, _, _ in spec]
    depth_of: dict[str, int] = {}
    for nid in order:
        ps = parents[nid]
        depth_of[nid] = 1 + (max(depth_of[p] for p in ps) if ps else 0)
    return {
        "depth": max(depth_of.values()),
        "max_fanin": max(len(ps) for _, ps, _ in spec),
        "has_min": int(any(agg == "min" for _, _, agg in spec)),
        "n_nodes": len(spec),
    }


def draw(topo: str, seed: int, base_skill: float, disp: float):
    rng = np.random.default_rng(seed)
    nodes = {}
    for nid, ps, agg in TOPOS[topo]:
        sk = float(np.clip(base_skill + rng.uniform(-disp, disp), 0.30, 0.95))
        ca = float(np.clip(CATCH0 + rng.uniform(-disp, disp), 0.30, 0.95))
        nodes[nid] = (sk, ca, ps, agg)
    order = [nid for nid, _, _ in TOPOS[topo]]
    children = {nid: [] for nid in order}
    for nid, ps, _ in TOPOS[topo]:
        for p in ps:
            children[p].append(nid)
    sinks = [nid for nid in order if not children[nid]]
    return nodes, order, sinks


def qg_given(sigma_raw, b, nodes, order, sinks):
    corr = {}
    for n in order:
        _, catch, ps, agg = nodes[n]
        # effective skill not needed here (we score corrected from current raw + b)
        corr[n] = F.sigma_corr_fixed_point(sigma_raw[n], b[n] * catch, 1.0)
    return min(corr[s] for s in sinks), corr


def greedy_resolve(sigma_raw, nodes, order, sinks):
    """Strong deployable comparator: at each observation re-solve the full allocation
    from scratch by greedy marginal water-filling to feasibility (vs the MSO
    controller's single increment). The per-step delivered-quality objective is
    separable across sinks and monotone, so this attains the per-step optimum up to
    the DREVIEW grid (the closed-form optimum is online_control.optimal_allocation;
    equivalence checked in tests/test_online_control.py)."""
    b = {n: 0.0 for n in order}
    cur = qg_given(sigma_raw, b, nodes, order, sinks)[0]
    while cur < P_MIN:
        best, bg = None, 0.0
        for n in order:
            if b[n] + DREVIEW > BMAX:
                continue
            trial = dict(b); trial[n] += DREVIEW
            g = qg_given(sigma_raw, trial, nodes, order, sinks)[0] - cur
            if g > bg:
                best, bg = n, g
        if best is None:
            break
        b[best] = min(b[best] + DREVIEW, BMAX)
        cur = qg_given(sigma_raw, b, nodes, order, sinks)[0]
    return b


def mab_select(mab_N, mab_X, b, order, sigma_raw, nodes, sinks, qg):
    """Discounted-UCB node choice + observed-reward update (model-free baseline).

    Arms = nodes with headroom; reward = OBSERVED normalized Delta Q_G of the pulled
    arm (bandit feedback -- no graph, no marginal formula). Drift is tracked by
    discounting (GAMMA_MAB), so the changing best-arm is followed without the model.
    """
    for n in order:
        mab_N[n] *= GAMMA_MAB
        mab_X[n] *= GAMMA_MAB
    avail = [n for n in order if b[n] + DREVIEW <= BMAX]
    if not avail:
        return
    sel = next((n for n in avail if mab_N[n] < 1e-9), None)  # forced exploration
    if sel is None:
        total = sum(mab_N[n] for n in avail)
        best_val = -1.0
        for n in avail:
            mean = mab_X[n] / mab_N[n]
            bonus = C_MAB * math.sqrt(math.log(max(total, 2.0)) / mab_N[n])
            if mean + bonus > best_val:
                best_val, sel = mean + bonus, n
    b[sel] = min(b[sel] + DREVIEW, BMAX)
    new_qg = qg_given(sigma_raw, b, nodes, order, sinks)[0]
    reward = max(0.0, min(1.0, (new_qg - qg) / DREVIEW))  # observed, normalized
    mab_N[sel] += 1.0
    mab_X[sel] += reward


def run(nodes, order, sinks, policy):
    sigma_raw = {n: nodes[n][0] * ETA / (ETA + DELTA_DECAY) for n in order}
    b = {n: (0.5 if policy == "fixed" else 0.0) for n in order}
    mab_N = {n: 0.0 for n in order}
    mab_X = {n: 0.0 for n in order}
    feas, review = 0, 0.0
    for t in range(T):
        corr = {}
        for n in order:
            sk0, catch, ps, agg = nodes[n]
            skill = max(0.30, sk0 - MU * t * DT)
            se = F.effective_skill(skill, [corr[p] for p in ps], agg) if ps else skill
            sigma_raw[n] = F.calibration_operator_step(sigma_raw[n], se, ETA, DELTA_DECAY, DT)
            corr[n] = F.sigma_corr_fixed_point(sigma_raw[n], b[n] * catch, 1.0)
        qg = min(corr[s] for s in sinks)
        feas += int(qg >= P_MIN)
        review += sum(b.values())
        if policy == "online-greedy":
            b = greedy_resolve(sigma_raw, nodes, order, sinks)
        elif policy == "online-mab" and qg < P_MIN:
            mab_select(mab_N, mab_X, b, order, sigma_raw, nodes, sinks, qg)
        elif policy in ("online-unif", "online-mso") and qg < P_MIN:
            if policy == "online-unif":
                for n in order:
                    b[n] = min(b[n] + DREVIEW / len(order), BMAX)
            else:
                best, bg = None, 0.0
                for n in order:
                    if b[n] + DREVIEW > BMAX:
                        continue
                    trial = dict(b); trial[n] += DREVIEW
                    g = qg_given(sigma_raw, trial, nodes, order, sinks)[0] - qg
                    if g > bg:
                        best, bg = n, g
                if best is not None:
                    b[best] = min(b[best] + DREVIEW, BMAX)
    return feas / T, review / T


def main() -> int:
    seeds, disp = range(40), 0.12
    rows = []
    for topo, seed in itertools.product(TOPOS, seeds):
        nodes, order, sinks = draw(topo, seed, 0.78, disp)
        f_fixed, _ = run(nodes, order, sinks, "fixed")
        f_unif, c_unif = run(nodes, order, sinks, "online-unif")
        f_mab, c_mab = run(nodes, order, sinks, "online-mab")
        f_grd, c_grd = run(nodes, order, sinks, "online-greedy")
        f_mso, c_mso = run(nodes, order, sinks, "online-mso")
        rows.append({"topo": topo, **features(topo),
                     "ite_vs_fixed": f_mso - f_fixed,
                     "ite_vs_unif": f_mso - f_unif,
                     "ite_vs_mab": f_mso - f_mab,
                     "ite_vs_greedy": f_mso - f_grd,
                     "review_mso": c_mso, "review_greedy": c_grd,
                     "review_unif": c_unif, "review_mab": c_mab})
    A = np.array([r["ite_vs_fixed"] for r in rows])
    U = np.array([r["ite_vs_unif"] for r in rows])
    M = np.array([r["ite_vs_mab"] for r in rows])
    R = np.array([r["ite_vs_greedy"] for r in rows])

    def ci(x):
        m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
        h = stats.t.ppf(0.975, len(x) - 1) * se
        return m, m - h, m + h

    print(f"Testbed: {len(TOPOS)} topologies x {len(seeds)} seeds = {len(rows)} paired units\n")
    m, lo, hi = ci(A)
    print(f"ATE online-MSO vs fixed     (Delta feasible-fraction): {m:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]")
    m, lo, hi = ci(U)
    print(f"ATE online-MSO vs uniform   (Delta feasible-fraction): {m:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]")
    m, lo, hi = ci(M)
    print(f"ATE online-MSO vs MAB (D-UCB)  (Delta feasible-fraction): {m:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]")
    m, lo, hi = ci(R)
    print(f"ATE online-MSO vs greedy re-solve (Delta feasible-fraction): {m:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]")
    print(f"\nMean review committed (time-avg sum_v b_v): "
          f"MSO={np.mean([r['review_mso'] for r in rows]):.3f}  "
          f"greedy-resolve={np.mean([r['review_greedy'] for r in rows]):.3f}  "
          f"MAB={np.mean([r['review_mab'] for r in rows]):.3f}  "
          f"uniform={np.mean([r['review_unif'] for r in rows]):.3f}")

    print("\nATE (vs fixed | vs uniform | vs MAB | vs greedy re-solve) by topology:")
    for topo in TOPOS:
        a = np.array([r["ite_vs_fixed"] for r in rows if r["topo"] == topo])
        u = np.array([r["ite_vs_unif"] for r in rows if r["topo"] == topo])
        mm = np.array([r["ite_vs_mab"] for r in rows if r["topo"] == topo])
        rr = np.array([r["ite_vs_greedy"] for r in rows if r["topo"] == topo])
        print(f"  {topo:8s} {a.mean():+.3f} | {u.mean():+.3f} | {mm.mean():+.3f} | {rr.mean():+.3f}")

    # Effect heterogeneity: OLS of the MSO-vs-uniform effect (the targeting benefit)
    # on motif features (standardized). Coefficient = contribution per +1 SD.
    feat = ["depth", "max_fanin", "has_min", "n_nodes"]
    X = np.array([[r[f] for f in feat] for r in rows], dtype=float)
    Xs = (X - X.mean(0)) / X.std(0)
    Xd = np.column_stack([np.ones(len(rows)), Xs])
    beta, *_ = np.linalg.lstsq(Xd, U, rcond=None)
    yhat = Xd @ beta
    r2 = 1 - ((U - yhat) ** 2).sum() / ((U - U.mean()) ** 2).sum()
    print("\nHeterogeneity of the MSO-vs-uniform effect (OLS on standardized motif "
          f"features; R^2={r2:.2f}):")
    print(f"  intercept (mean effect)      {beta[0]:+.3f}")
    for f, b in zip(feat, beta[1:]):
        print(f"  {f:24s} {b:+.3f}  per +1 SD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
