#!/usr/bin/env python3
"""Sensitivity analysis for MSO allocation: full-factorial sweep + ANOVA.

Factors (balanced full factorial):
    skill     baseline node competence sigma_skill, shared by all nodes
    budget    total review budget B (units: node-equivalents of full review;
              b_v=1 reviews every item at one node, so B is summed coverage)
    catch     reviewer catch rate c, shared by all nodes
    topology  chain3 | diamond | merge3 | fanout

Responses per cell:
    Q_G(MSO)      delivered sink quality under the MSO marginal policy
    advantage     Q_G(MSO) - max Q_G over the five baseline policies

A balanced design is orthogonal, so main-effect and two-way sums of squares are
computed from marginal means; three- and four-way interactions are pooled into
the residual. Reports eta^2 (variance explained) and an F-test per effect.

Run:  PYTHONPATH=src python3 scripts/sensitivity_analysis.py
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
_spec = importlib.util.spec_from_file_location(
    "wss", str(Path(__file__).resolve().parent / "wesaac_simulation_suite.py"))
wss = importlib.util.module_from_spec(_spec)
sys.modules["wss"] = wss
_spec.loader.exec_module(wss)

NodeSpec, WorkflowSpec = wss.NodeSpec, wss.WorkflowSpec

SKILL = [0.55, 0.65, 0.75, 0.85]
BUDGET = [0.5, 1.0, 1.5, 2.0, 2.5]
CATCH = [0.5, 0.7, 0.9]
TOPO = ["chain3", "diamond", "merge3", "fanout"]
P_MIN = 0.70
POLICIES = ["mso_marginal", "uniform", "weakest_raw",
            "corrected_only", "degree_first", "random"]
BASELINES = [p for p in POLICIES if p != "mso_marginal"]


# (node_id, parents, aggregation) skeleton per topology
_TOPO = {
    "chain3": [("n0", (), "product"), ("n1", ("n0",), "product"),
               ("n2", ("n1",), "product")],
    "diamond": [("src", (), "product"), ("a", ("src",), "product"),
                ("b", ("src",), "product"), ("m", ("a", "b"), "product")],
    "merge3": [("p0", (), "product"), ("p1", (), "product"), ("p2", (), "product"),
               ("d", ("p0", "p1", "p2"), "product")],
    "fanout": [("src", (), "product"), ("x0", ("src",), "product"),
               ("x1", ("src",), "product"), ("x2", ("src",), "product"),
               ("m", ("x0", "x1", "x2"), "mean")],
}


def make_workflow(topo: str, s, c, disp: float = 0.0, seed: int = 0) -> object:
    """Homogeneous (disp=0) or per-node-perturbed (disp>0) workflow.

    With disp>0 each node's skill/catch is drawn uniformly in [base+-disp],
    clipped to [0.30, 0.95], making the graph heterogeneous so allocation matters.
    """
    rng = np.random.default_rng(seed)
    nodes = []
    for nid, parents, agg in _TOPO[topo]:
        sk = float(np.clip(s + (rng.uniform(-disp, disp) if disp else 0.0), 0.30, 0.95))
        ca = float(np.clip(c + (rng.uniform(-disp, disp) if disp else 0.0), 0.30, 0.95))
        nodes.append(NodeSpec(nid, sk, ca, parents, agg))
    return WorkflowSpec(topo, tuple(nodes), p_min=P_MIN)


def q_of(wf, policy: str, B: float) -> float:
    if policy == "random":
        vals = [wss.evaluate(wf, wss.policy_budget(wf, policy, B, seed=1000 + k)).quality
                for k in range(5)]
        return float(np.mean(vals))
    return wss.evaluate(wf, wss.policy_budget(wf, policy, B, seed=1)).quality


def run_grid() -> pd.DataFrame:
    rows = []
    for s, B, c, topo in itertools.product(SKILL, BUDGET, CATCH, TOPO):
        wf = make_workflow(topo, s, c)
        qs = {p: q_of(wf, p, B) for p in POLICIES}
        best_base = max(qs[p] for p in BASELINES)
        rows.append({
            "skill": s, "budget": B, "catch": c, "topology": topo,
            "Q_mso": qs["mso_marginal"],
            "advantage": qs["mso_marginal"] - best_base,
            "feasible_mso": int(qs["mso_marginal"] >= P_MIN),
            **{f"Q_{p}": qs[p] for p in POLICIES},
        })
    return pd.DataFrame(rows)


def factorial_anova(df: pd.DataFrame, response: str,
                    factors=("skill", "budget", "catch", "topology")) -> pd.DataFrame:
    """Balanced full-factorial ANOVA: main + two-way; higher-order = residual."""
    y = df[response].to_numpy()
    G = y.mean()
    N = len(y)
    ss_total = float(((y - G) ** 2).sum())
    nlev = {f: df[f].nunique() for f in factors}

    effects = []
    # main effects
    for f in factors:
        m = df.groupby(f)[response].transform("mean").to_numpy()
        ss = float(((m - G) ** 2).sum())
        effects.append((f, ss, nlev[f] - 1))
    # two-way interactions
    for a, b in itertools.combinations(factors, 2):
        m_ab = df.groupby([a, b])[response].transform("mean").to_numpy()
        m_a = df.groupby(a)[response].transform("mean").to_numpy()
        m_b = df.groupby(b)[response].transform("mean").to_numpy()
        ss = float(((m_ab - m_a - m_b + G) ** 2).sum())
        effects.append((f"{a}:{b}", ss, (nlev[a] - 1) * (nlev[b] - 1)))

    ss_model = sum(e[1] for e in effects)
    df_model = sum(e[2] for e in effects)
    ss_resid = ss_total - ss_model
    df_resid = (N - 1) - df_model
    ms_resid = ss_resid / df_resid

    out = []
    for name, ss, dfree in effects:
        ms = ss / dfree
        F = ms / ms_resid
        p = float(stats.f.sf(F, dfree, df_resid))
        out.append({"effect": name, "df": dfree, "SS": ss,
                    "eta2_pct": 100 * ss / ss_total, "F": F, "p": p})
    out.append({"effect": "Residual (3+way)", "df": df_resid, "SS": ss_resid,
                "eta2_pct": 100 * ss_resid / ss_total, "F": np.nan, "p": np.nan})
    return pd.DataFrame(out).sort_values("eta2_pct", ascending=False)


def heterogeneity_sweep(B: float = 1.5, s: float = 0.70, c: float = 0.70,
                        seeds: int = 60) -> pd.DataFrame:
    """MSO advantage vs per-node parameter dispersion (averaged over seeds)."""
    rows = []
    for disp in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]:
        adv_wr, adv_best = [], []
        for topo in TOPO:
            for seed in range(seeds):
                wf = make_workflow(topo, s, c, disp=disp, seed=seed)
                qm = q_of(wf, "mso_marginal", B)
                qwr = q_of(wf, "weakest_raw", B)
                qbest = max(q_of(wf, p, B) for p in BASELINES)
                adv_wr.append(qm - qwr)
                adv_best.append(qm - qbest)
        rows.append({"dispersion": disp,
                     "adv_vs_weakest_raw": float(np.mean(adv_wr)),
                     "adv_vs_best_baseline": float(np.mean(adv_best)),
                     "max_adv_vs_best": float(np.max(adv_best))})
    return pd.DataFrame(rows)


def main() -> int:
    df = run_grid()
    outdir = REPO / "tmp" / "sensitivity"
    outdir.mkdir(parents=True, exist_ok=True)
    df.to_csv(outdir / "grid.csv", index=False)
    print(f"grid: {len(df)} cells "
          f"({len(SKILL)}x{len(BUDGET)}x{len(CATCH)}x{len(TOPO)})")

    print("\n=== Policy ranking across the full grid (mean Q_G, feasibility @ p_min=0.70) ===")
    for p in POLICIES:
        q = df[f"Q_{p}"]
        feas = (q >= P_MIN).mean()
        print(f"  {p:15s} meanQ={q.mean():.3f}  sd={q.std():.3f}  feasible={feas:.0%}")
    print(f"\nMSO advantage over best baseline: mean={df['advantage'].mean():+.3f} "
          f"(min {df['advantage'].min():+.3f}, max {df['advantage'].max():+.3f}); "
          f"MSO >= best baseline in {(df['advantage'] >= -1e-9).mean():.0%} of cells")

    for resp in ["Q_mso", "advantage"]:
        print(f"\n=== ANOVA: {resp} ~ skill * budget * catch * topology ===")
        a = factorial_anova(df, resp)
        with pd.option_context("display.float_format", lambda v: f"{v:.3f}"):
            print(a.to_string(index=False))

    print("\n=== Heterogeneity sweep: MSO advantage vs per-node dispersion "
          "(B=1.5, base skill=catch=0.70, 60 seeds x 4 topologies) ===")
    hs = heterogeneity_sweep()
    hs.to_csv(outdir / "heterogeneity.csv", index=False)
    with pd.option_context("display.float_format", lambda v: f"{v:.4f}"):
        print(hs.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
