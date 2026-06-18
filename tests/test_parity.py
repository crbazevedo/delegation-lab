"""Parity test: the browser port (web/mso-core.js) must equal the Python reference.

This pins every equation in `web/mso-core.js` to `minimal_oversight._formulae`
and `minimal_oversight.capacity`. Both sides compute from the SAME inputs at test
time — neither trusts a stored snapshot — and must agree to within 1e-6.

Skipped automatically when Node.js is unavailable. Add Node to CI to enforce.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from minimal_oversight import _formulae as F
from minimal_oversight import analyze_pipeline
from minimal_oversight import estimation as E
from minimal_oversight.allocation import select_scope
from minimal_oversight.capacity import check_feasibility
from minimal_oversight.models import AggregationType, Node, PipelineGraph
from minimal_oversight.topology import delegation_centrality, detect_motifs

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts" / "parity_runner.js"
TOL = 1e-6

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="Node.js not available; parity test requires node",
)

_AGG = {
    "product": AggregationType.PRODUCT,
    "min": AggregationType.WEAKEST_LINK,
    "mean": AggregationType.WEIGHTED_MEAN,
}


def _nd(node_id, skill, catch, parents, agg="product"):
    return {
        "id": node_id,
        "sigma_skill": skill,
        "catch_rate": catch,
        "parents": parents,
        "aggregation": agg,
    }


# --- Shared fixtures (inputs only; both sides compute outputs from these) ---
SIGMAS = [0.05, 0.1, 0.25, 0.375, 0.417, 0.5, 0.517, 0.667, 0.708, 0.85, 0.95]

PIPE_SALES = {
    "nodes": [
        _nd("lead_enrich", 0.80, 0.60, []),
        _nd("lead_score", 0.62, 0.65, ["lead_enrich"]),
        _nd("outreach_draft", 0.50, 0.55, ["lead_score"]),
        _nd("deal_forecast", 0.45, 0.70, ["lead_score"]),
        _nd("crm_write", 0.85, 0.70, ["outreach_draft", "deal_forecast"]),
        _nd("meeting_book", 0.65, 0.60, ["crm_write"]),
    ]
}
PIPE_CHAIN = {
    "nodes": [
        _nd("a", 0.7, 0.65, []),
        _nd("b", 0.6, 0.6, ["a"], "min"),
        _nd("c", 0.75, 0.7, ["b"], "mean"),
    ]
}
PIPE_LINE = {
    "nodes": [
        _nd("a", 0.7, 0.65, []),
        _nd("b", 0.6, 0.6, ["a"]),
        _nd("c", 0.72, 0.6, ["b"]),
        _nd("d", 0.66, 0.6, ["c"]),
    ]
}

CASES = {
    "fisher": SIGMAS,
    "volume": SIGMAS,
    "sraw_fp": [[0.55, 10, 2, 0], [0.8, 10, 2, 0], [0.45, 10, 2, 0.1], [0.62, 8, 3, 0]],
    "scorr": [[0.5167, 0.65], [0.375, 0.70], [0.708, 0.70], [0.2, 0.9]],
    "masking": [[0.83, 0.5167], [0.8125, 0.375], [0.9125, 0.708]],
    "eff_skill": [
        [0.85, [0.7012, 0.7908], "product"],
        [0.6, [0.8, 0.5], "min"],
        [0.75, [0.9, 0.6], "mean"],
        [0.5, [], "product"],
    ],
    "opt_auth": [[[0.3, 0.5, 0.7, 0.9], 5.0, 1.0], [[0.4, 0.6], 12.0, 1.0]],
    "solve_lambda": [[[0.6, 0.7, 0.75, 0.8], 0.4], [[0.5, 0.55, 0.6], 0.35]],
    "buffer": [[0.78, 0.70, 0.02, 1.5], [0.777, 0.80, 0.02, 0.0]],
    "autonomy": [[0.78, 0.70, 0.02, 1.0, 0.1], [0.78, 0.70, 0.02, 1.0, 0.4]],
    "crit_entropy": [[0.78, 0.70, 0.02], [0.85, 0.60, 0.02]],
    "pipelines": [
        {"pipeline": PIPE_SALES, "p_min": 0.80, "hw": 0.0},
        {"pipeline": PIPE_SALES, "p_min": 0.70, "hw": 1.5},
        {"pipeline": PIPE_CHAIN, "p_min": 0.75, "hw": 0.5},
    ],
    "centrality": [
        {"pipeline": PIPE_SALES, "names": [n["id"] for n in PIPE_SALES["nodes"]]},
        {"pipeline": PIPE_LINE, "names": [n["id"] for n in PIPE_LINE["nodes"]]},
    ],
    "motifs": [PIPE_SALES, PIPE_LINE, PIPE_CHAIN],
    "risk": [PIPE_SALES, PIPE_LINE],
    "ro_step": [
        [0.5, 0.55, 10, 2, 0.1, 0],
        [0.3, 0.8, 10, 2, 0.05, 0.1],
        [0.9, 0.4, 8, 3, 0.1, 0],
    ],
    "ro_traj": [
        {"init": 0.5, "skill": 0.55, "eta": 10, "delta": 2, "dt": 0.1, "sigma0": 0, "steps": 400},
        {"init": 0.2, "skill": 0.7, "eta": 10, "delta": 2,
         "dt": 0.05, "sigma0": 0.1, "steps": 200},
    ],
    "scope": [
        {"sigma": [0.667, 0.517, 0.417, 0.375, 0.708, 0.542], "p_min": 0.5, "coverage": 0.0},
        {"sigma": [0.8, 0.4, 0.6, 0.3, 0.7], "p_min": 0.6, "coverage": 0.5},
    ],
    # web/mso-estimate.js turns a practitioner's real outcomes into per-node
    # sigma_raw / sigma_corr / catch / masking. Pin those to estimation.py.
    "estimate": [
        {"raw": [1, 0, 1, 1, 0, 1, 0, 1, 1, 0], "corr": [1, 1, 1, 1, 0, 1, 1, 1, 1, 0]},
        {"raw": [1, 0, 0, 1, 0, 0, 1, 0], "corr": [1, 1, 0, 1, 1, 0, 1, 1]},
        {"raw": [1, 1, 1, 0], "corr": [1, 1, 1, 1]},
    ],
}

SCALAR_KEYS = [
    "fisher",
    "volume",
    "sraw_fp",
    "scorr",
    "masking",
    "eff_skill",
    "buffer",
    "autonomy",
    "crit_entropy",
    "ro_step",
    "ro_traj",
]


def _build_graph(spec: dict) -> PipelineGraph:
    nodes = [
        Node(
            n["id"],
            sigma_skill=n["sigma_skill"],
            catch_rate=n["catch_rate"],
            aggregation=_AGG[n["aggregation"]],
        )
        for n in spec["nodes"]
    ]
    g = PipelineGraph(nodes)
    for n in spec["nodes"]:
        for p in n["parents"]:
            g.add_edge(p, n["id"])
    return g


def _node_masking(spec: dict) -> dict:
    masking = {}
    for n in spec["nodes"]:
        lsr = F.sigma_raw_fixed_point(n["sigma_skill"], 10, 2, 0)
        lsc = F.sigma_corr_fixed_point(lsr, n["catch_rate"])
        masking[n["id"]] = F.masking_index(lsc, lsr)
    return masking


def _python_expected() -> dict:
    exp: dict = {}
    exp["fisher"] = [float(F.fisher_information(s)) for s in CASES["fisher"]]
    exp["volume"] = [float(F.fisher_volume_element(s)) for s in CASES["volume"]]
    exp["sraw_fp"] = [F.sigma_raw_fixed_point(*a) for a in CASES["sraw_fp"]]
    exp["scorr"] = [F.sigma_corr_fixed_point(*a) for a in CASES["scorr"]]
    exp["masking"] = [F.masking_index(*a) for a in CASES["masking"]]
    exp["eff_skill"] = [F.effective_skill(a[0], a[1], a[2]) for a in CASES["eff_skill"]]
    exp["opt_auth"] = [F.optimal_authority(a[0], a[1], a[2]).tolist() for a in CASES["opt_auth"]]
    exp["solve_lambda"] = []
    for a in CASES["solve_lambda"]:
        lam = F.solve_lambda(a[0], a[1])
        exp["solve_lambda"].append({"lam": lam, "alpha": F.optimal_authority(a[0], lam).tolist()})
    exp["buffer"] = [F.effective_autonomy_buffer(*a) for a in CASES["buffer"]]
    exp["autonomy"] = [F.autonomy_time(*a) for a in CASES["autonomy"]]
    exp["crit_entropy"] = [F.critical_entropy(*a) for a in CASES["crit_entropy"]]
    exp["ro_step"] = [F.return_operator_step(*a) for a in CASES["ro_step"]]
    exp["ro_traj"] = []
    for c in CASES["ro_traj"]:
        s = c["init"]
        for _ in range(c["steps"]):
            s = F.return_operator_step(s, c["skill"], c["eta"], c["delta"], c["dt"], c["sigma0"])
        exp["ro_traj"].append(s)
    exp["estimate"] = []
    for c in CASES["estimate"]:
        s_raw = E.estimate_sigma_raw(c["raw"])
        s_corr = E.estimate_sigma_corr(c["corr"])
        exp["estimate"].append({
            "sigma_raw": s_raw,
            "sigma_corr": s_corr,
            "masking": E.estimate_masking_index(s_corr, s_raw),
            "catch": E.estimate_catch_rate(c["raw"], c["corr"]),
        })
    exp["scope"] = []
    for c in CASES["scope"]:
        r = select_scope(c["sigma"], c["p_min"], c["coverage"])
        exp["scope"].append({
            "delegated": r.delegated_tasks, "coverage": r.coverage,
            "cost": r.total_cost, "avg": r.avg_sigma_delegated,
        })
    exp["pipelines"] = []
    for pc in CASES["pipelines"]:
        g = _build_graph(pc["pipeline"])
        rep = check_feasibility(g, p_min=pc["p_min"], process_entropy=pc["hw"])
        exp["pipelines"].append(
            {
                "cop": rep.c_op,
                "beff": rep.b_eff,
                "hcrit": rep.h_crit,
                "bottleneck": rep.bottleneck_node,
                "feasible": rep.feasible,
                "masking": _node_masking(pc["pipeline"]),
            }
        )
    exp["centrality"] = []
    for c in CASES["centrality"]:
        g = _build_graph(c["pipeline"])
        exp["centrality"].append([delegation_centrality(g, n) for n in c["names"]])
    exp["motifs"] = []
    for spec in CASES["motifs"]:
        g = _build_graph(spec)
        exp["motifs"].append(sorted(mi.risk_description for mi in detect_motifs(g)))
    exp["risk"] = []
    for spec in CASES["risk"]:
        g = _build_graph(spec)
        rep = analyze_pipeline(g, p_min=0.80)
        exp["risk"].append([
            {
                "name": r.name,
                "sota": r.sota_score,
                "dc": r.delegation_centrality,
                "masking": r.masking_index,
                "fi": r.fan_in_degree,
                "fo": r.fan_out_degree,
                "bott": r.is_bottleneck,
            }
            for r in rep.node_risks
        ])
    return exp


def _close(a, b, tol=TOL):
    if isinstance(a, list):
        assert len(a) == len(b)
        return all(_close(x, y, tol) for x, y in zip(a, b))
    if a == float("inf") or b == float("inf"):
        return a == b
    return abs(a - b) <= tol + tol * abs(b)


def _run_node(cases: dict) -> dict:
    with tempfile.TemporaryDirectory() as d:
        in_path = Path(d) / "in.json"
        out_path = Path(d) / "out.json"
        in_path.write_text(json.dumps(cases))
        subprocess.run(
            ["node", str(RUNNER), str(in_path), str(out_path)],
            check=True,
            stdin=subprocess.DEVNULL,
        )
        return json.loads(out_path.read_text())


def test_browser_port_matches_python_reference():
    got = _run_node(CASES)
    exp = _python_expected()

    for key in SCALAR_KEYS:
        assert _close(got[key], exp[key]), f"mismatch in {key}"

    for g, e in zip(got["opt_auth"], exp["opt_auth"]):
        assert _close(g, e), "opt_auth mismatch"

    for g, e in zip(got["solve_lambda"], exp["solve_lambda"]):
        assert _close(g["alpha"], e["alpha"]), "alpha mismatch"
        assert _close(g["lam"], e["lam"], tol=1e-5), "lambda mismatch"

    for g, e in zip(got["pipelines"], exp["pipelines"]):
        assert g["bottleneck"] == e["bottleneck"], "bottleneck mismatch"
        assert g["feasible"] == e["feasible"]
        for k in ["cop", "beff", "hcrit"]:
            assert _close(g[k], e[k]), f"pipeline {k} mismatch"
        for node_id in e["masking"]:
            assert _close(g["masking"][node_id], e["masking"][node_id]), f"masking {node_id}"

    for g, e in zip(got["estimate"], exp["estimate"]):
        for k in ["sigma_raw", "sigma_corr", "masking", "catch"]:
            assert _close(g[k], e[k]), f"estimate {k} mismatch"

    for g, e in zip(got["scope"], exp["scope"]):
        assert g["delegated"] == e["delegated"], "scope delegated mismatch"
        for k in ["coverage", "cost", "avg"]:
            assert _close(g[k], e[k]), f"scope {k} mismatch"

    for g, e in zip(got["centrality"], exp["centrality"]):
        assert _close(g, e), "delegation centrality mismatch"

    for g, e in zip(got["motifs"], exp["motifs"]):
        assert g == e, f"motif mismatch:\n  js={g}\n  py={e}"

    for gr, er in zip(got["risk"], exp["risk"]):
        assert [x["name"] for x in gr] == [x["name"] for x in er], "risk ranking order mismatch"
        for gn, en in zip(gr, er):
            assert gn["fi"] == en["fi"] and gn["fo"] == en["fo"] and gn["bott"] == en["bott"]
            for k in ["sota", "dc", "masking"]:
                assert _close(gn[k], en[k]), f"risk {en['name']} {k} mismatch"
