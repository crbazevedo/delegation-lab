"""Parity test: the browser port (web/mso-core.js) must equal the Python reference.

This pins every equation in `web/mso-core.js` to `minimal_oversight._formulae`
and `minimal_oversight.capacity`. Both sides compute from the SAME inputs at test
time — neither trusts a stored snapshot — and must agree to within 1e-6.

Skipped automatically when Node.js is unavailable. Add Node to CI to enforce.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from minimal_oversight import _formulae as F
from minimal_oversight.capacity import check_feasibility
from minimal_oversight.models import AggregationType, Node, PipelineGraph

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts" / "parity_runner.js"
TOL = 1e-6

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js not available; parity test requires node"
)

_AGG = {"product": AggregationType.PRODUCT, "min": AggregationType.WEAKEST_LINK, "mean": AggregationType.WEIGHTED_MEAN}

# --- Shared fixtures (inputs only; both sides compute outputs from these) ---
SIGMAS = [0.05, 0.1, 0.25, 0.375, 0.417, 0.5, 0.517, 0.667, 0.708, 0.85, 0.95]

PIPE_SALES = {
    "nodes": [
        {"id": "lead_enrich", "sigma_skill": 0.80, "catch_rate": 0.60, "parents": [], "aggregation": "product"},
        {"id": "lead_score", "sigma_skill": 0.62, "catch_rate": 0.65, "parents": ["lead_enrich"], "aggregation": "product"},
        {"id": "outreach_draft", "sigma_skill": 0.50, "catch_rate": 0.55, "parents": ["lead_score"], "aggregation": "product"},
        {"id": "deal_forecast", "sigma_skill": 0.45, "catch_rate": 0.70, "parents": ["lead_score"], "aggregation": "product"},
        {"id": "crm_write", "sigma_skill": 0.85, "catch_rate": 0.70, "parents": ["outreach_draft", "deal_forecast"], "aggregation": "product"},
        {"id": "meeting_book", "sigma_skill": 0.65, "catch_rate": 0.60, "parents": ["crm_write"], "aggregation": "product"},
    ]
}
PIPE_CHAIN = {
    "nodes": [
        {"id": "a", "sigma_skill": 0.7, "catch_rate": 0.65, "parents": [], "aggregation": "product"},
        {"id": "b", "sigma_skill": 0.6, "catch_rate": 0.6, "parents": ["a"], "aggregation": "min"},
        {"id": "c", "sigma_skill": 0.75, "catch_rate": 0.7, "parents": ["b"], "aggregation": "mean"},
    ]
}

CASES = {
    "fisher": SIGMAS,
    "volume": SIGMAS,
    "sraw_fp": [[0.55, 10, 2, 0], [0.8, 10, 2, 0], [0.45, 10, 2, 0.1], [0.62, 8, 3, 0]],
    "scorr": [[0.5167, 0.65], [0.375, 0.70], [0.708, 0.70], [0.2, 0.9]],
    "masking": [[0.83, 0.5167], [0.8125, 0.375], [0.9125, 0.708]],
    "eff_skill": [[0.85, [0.7012, 0.7908], "product"], [0.6, [0.8, 0.5], "min"], [0.75, [0.9, 0.6], "mean"], [0.5, [], "product"]],
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
}


def _build_graph(spec: dict) -> PipelineGraph:
    nodes = [
        Node(n["id"], sigma_skill=n["sigma_skill"], catch_rate=n["catch_rate"], aggregation=_AGG[n["aggregation"]])
        for n in spec["nodes"]
    ]
    g = PipelineGraph(nodes)
    for n in spec["nodes"]:
        for p in n["parents"]:
            g.add_edge(p, n["id"])
    return g


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
    exp["pipelines"] = []
    for pc in CASES["pipelines"]:
        g = _build_graph(pc["pipeline"])
        rep = check_feasibility(g, p_min=pc["p_min"], process_entropy=pc["hw"])
        masking = {}
        for n in pc["pipeline"]["nodes"]:
            lsr = F.sigma_raw_fixed_point(n["sigma_skill"], 10, 2, 0)
            lsc = F.sigma_corr_fixed_point(lsr, n["catch_rate"])
            masking[n["id"]] = F.masking_index(lsc, lsr)
        exp["pipelines"].append({
            "cop": rep.c_op, "beff": rep.b_eff, "hcrit": rep.h_crit,
            "bottleneck": rep.bottleneck_node, "feasible": rep.feasible, "masking": masking,
        })
    return exp


def _close(a, b, tol=TOL):
    if isinstance(a, list):
        assert len(a) == len(b)
        return all(_close(x, y, tol) for x, y in zip(a, b))
    if a == float("inf") or b == float("inf"):
        return a == b
    return abs(a - b) <= tol + tol * abs(b)


def test_browser_port_matches_python_reference():
    with tempfile.TemporaryDirectory() as d:
        in_path = Path(d) / "in.json"
        out_path = Path(d) / "out.json"
        in_path.write_text(json.dumps(CASES))
        subprocess.run(["node", str(RUNNER), str(in_path), str(out_path)], check=True, stdin=subprocess.DEVNULL)
        got = json.loads(out_path.read_text())

    exp = _python_expected()

    for key in ["fisher", "volume", "sraw_fp", "scorr", "masking", "eff_skill", "buffer", "autonomy", "crit_entropy"]:
        assert _close(got[key], exp[key]), f"mismatch in {key}: {got[key]} != {exp[key]}"

    for g, e in zip(got["opt_auth"], exp["opt_auth"]):
        assert _close(g, e), f"opt_auth mismatch: {g} != {e}"

    for g, e in zip(got["solve_lambda"], exp["solve_lambda"]):
        assert _close(g["alpha"], e["alpha"]), f"alpha mismatch: {g['alpha']} != {e['alpha']}"
        assert _close(g["lam"], e["lam"], tol=1e-5), f"lambda mismatch: {g['lam']} != {e['lam']}"

    for g, e in zip(got["pipelines"], exp["pipelines"]):
        assert g["bottleneck"] == e["bottleneck"], f"bottleneck: {g['bottleneck']} != {e['bottleneck']}"
        assert g["feasible"] == e["feasible"]
        for k in ["cop", "beff", "hcrit"]:
            assert _close(g[k], e[k]), f"pipeline {k}: {g[k]} != {e[k]}"
        for node_id in e["masking"]:
            assert _close(g["masking"][node_id], e["masking"][node_id]), f"masking {node_id}"
