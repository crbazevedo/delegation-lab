#!/usr/bin/env python3
"""Debiased motif-contribution estimate on a random-DAG ensemble.

The hand-picked 8-topology testbed confounds motif features (they co-vary by
design), so a heterogeneity regression on it is biased. Here we sample a large
Erdos-Renyi DAG ensemble instead -- a random topological order, each upper-
triangular edge i.i.d. Bernoulli(p), sweeping size n and density p. (A Wishart
prior is *not* applicable: it samples symmetric positive-definite covariance
matrices, whereas a DAG adjacency is binary and strictly upper-triangular.)

Each DAG carries motif features (depth, max fan-in, node count, fraction of
min-gates, edge density). We run the same paired counterfactual as before (same
DAG + same drift under each policy), then (1) report the average treatment effect
of online-MSO, (2) check feature collinearity by Variance Inflation Factor so the
partial contributions are identifiable, and (3) regress the per-DAG effect on
standardized features (OLS) for the debiased motif contributions.

Run:  PYTHONPATH=src python3 scripts/online_random_dags.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from minimal_oversight import _formulae as F  # noqa: E402
from minimal_oversight.online_control import (  # noqa: E402
    Workflow, delivered_quality, online_step, optimal_allocation,
)


def greedy_resolve(sigma_raw, wf, p_min, delta, b_max):
    """Strong deployable comparator: at each observation re-solve the full review
    allocation from scratch by greedy marginal water-filling to feasibility (vs the
    MSO controller's single increment). Because delivered_quality is separable across
    sinks and monotone, this greedy water-fill attains the per-step optimum up to the
    delta grid (the closed-form optimum is online_control.optimal_allocation; the
    equivalence is checked in tests/test_online_control.py)."""
    budget = {v: 0.0 for v in wf.order}
    cap = len(wf.order) * (int(b_max / delta) + 1) + 1
    for _ in range(cap):
        if delivered_quality(sigma_raw, budget, wf) >= p_min:
            break
        nxt = online_step(sigma_raw, budget, wf, p_min, delta, b_max)
        if nxt == budget:
            break
        budget = nxt
    return budget

ETA, DELTA_DECAY, MU = 10.0, 2.0, 0.010
P_MIN, T, DT, DREVIEW, BMAX = 0.58, 200, 0.1, 0.05, 1.0
GAMMA_MAB, C_MAB = 0.95, 0.4  # discounted-UCB: drift discount + exploration coef
AGGS = ("product", "min", "mean")


def sample_dag(n, p, rng):
    """Erdos-Renyi DAG on topo order 0..n-1; returns Workflow + per-node skill0."""
    spec, skill0 = [], {}
    for i in range(n):
        parents = tuple(f"x{j}" for j in range(i) if rng.random() < p)
        agg = rng.choice(AGGS) if len(parents) > 1 else "product"
        c = float(np.clip(0.70 + rng.uniform(-0.12, 0.12), 0.3, 0.95))
        spec.append((f"x{i}", c, parents, agg, 1.0))
        skill0[f"x{i}"] = float(np.clip(0.78 + rng.uniform(-0.12, 0.12), 0.3, 0.95))
    return Workflow.build(spec), skill0


def features(wf: Workflow) -> dict:
    depth = {}
    for v in wf.order:
        ps = wf.parents[v]
        depth[v] = 1 + (max(depth[p] for p in ps) if ps else 0)
    multi = [v for v in wf.order if len(wf.parents[v]) > 1]
    n_edges = sum(len(wf.parents[v]) for v in wf.order)
    return {
        "depth": max(depth.values()),
        "max_fanin": max((len(wf.parents[v]) for v in wf.order), default=0),
        "n_nodes": len(wf.order),
        "frac_min": (sum(wf.agg[v] == "min" for v in multi) / len(multi)) if multi else 0.0,
        "density": n_edges / len(wf.order),
    }


def mab_step(sigma_raw, budget, wf, mab_N, mab_X):
    """Discounted-UCB node choice + observed-reward update (model-free baseline):
    arms = nodes with headroom, reward = observed normalized Delta delivered quality
    (bandit feedback only; no graph or marginal formula). Returns new budget dict."""
    for v in wf.order:
        mab_N[v] *= GAMMA_MAB
        mab_X[v] *= GAMMA_MAB
    avail = [v for v in wf.order if budget[v] + DREVIEW <= BMAX]
    if not avail:
        return budget
    sel = next((v for v in avail if mab_N[v] < 1e-9), None)  # forced exploration
    if sel is None:
        total = sum(mab_N[v] for v in avail)
        best = -1.0
        for v in avail:
            ucb = mab_X[v] / mab_N[v] + C_MAB * math.sqrt(math.log(max(total, 2.0)) / mab_N[v])
            if ucb > best:
                best, sel = ucb, v
    q0 = delivered_quality(sigma_raw, budget, wf)
    budget = dict(budget)
    budget[sel] = min(budget[sel] + DREVIEW, BMAX)
    reward = max(0.0, min(1.0, (delivered_quality(sigma_raw, budget, wf) - q0) / DREVIEW))
    mab_N[sel] += 1.0
    mab_X[sel] += reward
    return budget


def feasible_fraction(wf, skill0, policy):
    """Returns (feasible_fraction, time-averaged review committed)."""
    sigma_raw = {v: skill0[v] * ETA / (ETA + DELTA_DECAY) for v in wf.order}
    budget = {v: (0.5 if policy == "fixed" else 0.0) for v in wf.order}
    mab_N = {v: 0.0 for v in wf.order}
    mab_X = {v: 0.0 for v in wf.order}
    feas, review = 0, 0.0
    for t in range(T):
        corr = {}
        for v in wf.order:
            ps = wf.parents[v]
            skill = max(0.30, skill0[v] - MU * t * DT)
            se = F.effective_skill(skill, [corr[p] for p in ps], wf.agg[v]) if ps else skill
            sigma_raw[v] = F.calibration_operator_step(sigma_raw[v], se, ETA, DELTA_DECAY, DT)
            corr[v] = F.sigma_corr_fixed_point(sigma_raw[v], budget[v] * wf.catch[v], wf.fix[v])
        qg = min(corr[s] for s in wf.sinks)
        feas += int(qg >= P_MIN)
        review += sum(budget.values())
        if policy == "online-mso":
            budget = online_step(sigma_raw, budget, wf, P_MIN, DREVIEW, BMAX)
        elif policy == "online-greedy":
            budget = greedy_resolve(sigma_raw, wf, P_MIN, DREVIEW, BMAX)
        elif policy == "online-mab" and qg < P_MIN:
            budget = mab_step(sigma_raw, budget, wf, mab_N, mab_X)
        elif policy == "online-unif" and qg < P_MIN:
            budget = {v: min(budget[v] + DREVIEW / len(wf.order), BMAX) for v in wf.order}
    return feas / T, review / T


def vif(X: np.ndarray) -> np.ndarray:
    """Variance inflation factor per column (collinearity diagnostic)."""
    out = []
    for j in range(X.shape[1]):
        y = X[:, j]
        others = np.delete(X, j, axis=1)
        A = np.column_stack([np.ones(len(y)), others])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        r2 = 1 - ((y - A @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        out.append(1.0 / max(1e-9, 1 - r2))
    return np.array(out)


def main() -> int:
    rng = np.random.default_rng(0)
    feat_names = ["depth", "max_fanin", "n_nodes", "frac_min", "density"]
    rows = []
    for n in (4, 5, 6, 7, 8):
        for p in (0.30, 0.45, 0.60):
            for k in range(40):
                wf, skill0 = sample_dag(n, p, rng)
                if not wf.sinks:
                    continue
                f_fixed, _ = feasible_fraction(wf, skill0, "fixed")
                f_unif, c_unif = feasible_fraction(wf, skill0, "online-unif")
                f_mab, c_mab = feasible_fraction(wf, skill0, "online-mab")
                f_grd, c_grd = feasible_fraction(wf, skill0, "online-greedy")
                f_mso, c_mso = feasible_fraction(wf, skill0, "online-mso")
                rows.append({**features(wf),
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
        m = x.mean(); h = stats.t.ppf(.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
        return m, m - h, m + h

    print(f"Erdos-Renyi DAG ensemble: {len(rows)} graphs "
          f"(n in 4..8, p in {{.30,.45,.60}}, 40 seeds each)\n")
    m, lo, hi = ci(A); print(f"ATE online-MSO vs fixed       : {m:+.3f}  95% CI [{lo:+.3f},{hi:+.3f}]")
    m, lo, hi = ci(U); print(f"ATE online-MSO vs uniform     : {m:+.3f}  95% CI [{lo:+.3f},{hi:+.3f}]")
    m, lo, hi = ci(M); print(f"ATE online-MSO vs MAB (D-UCB)   : {m:+.3f}  95% CI [{lo:+.3f},{hi:+.3f}]")
    m, lo, hi = ci(R); print(f"ATE online-MSO vs greedy re-solve: {m:+.3f}  95% CI [{lo:+.3f},{hi:+.3f}]")
    print(f"\nMean review committed (time-avg sum_v b_v): "
          f"MSO={np.mean([r['review_mso'] for r in rows]):.3f}  "
          f"greedy-resolve={np.mean([r['review_greedy'] for r in rows]):.3f}  "
          f"MAB={np.mean([r['review_mab'] for r in rows]):.3f}  "
          f"uniform={np.mean([r['review_unif'] for r in rows]):.3f}")

    X = np.array([[r[f] for f in feat_names] for r in rows], dtype=float)
    print("\nFeature collinearity (VIF; <5 = identifiable):")
    for name, v in zip(feat_names, vif((X - X.mean(0)) / X.std(0))):
        print(f"  {name:10s} VIF={v:.2f}")

    Xs = (X - X.mean(0)) / X.std(0)
    Xd = np.column_stack([np.ones(len(rows)), Xs])
    beta, *_ = np.linalg.lstsq(Xd, U, rcond=None)
    yhat = Xd @ beta
    r2 = 1 - ((U - yhat) ** 2).sum() / ((U - U.mean()) ** 2).sum()
    # standard errors for the coefficients
    dof = len(rows) - Xd.shape[1]
    mse = ((U - yhat) ** 2).sum() / dof
    cov = mse * np.linalg.inv(Xd.T @ Xd)
    se = np.sqrt(np.diag(cov))
    print(f"\nDebiased motif contributions to the MSO-vs-uniform effect "
          f"(OLS, standardized; R^2={r2:.2f}):")
    print(f"  {'intercept':12s} {beta[0]:+.4f}")
    for name, b, s in zip(feat_names, beta[1:], se[1:]):
        sig = "*" if abs(b / s) > 1.96 else " "
        print(f"  {name:12s} {b:+.4f}  (SE {s:.4f}){sig}  per +1 SD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
