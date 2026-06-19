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
from minimal_oversight import priors as P
from minimal_oversight import optimize as OPT
from minimal_oversight import registry as REG
from minimal_oversight.complexity import effective_sigma as _eff
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


def _nd(node_id, skill, catch, parents, agg="product", fix=None):
    return {
        "id": node_id,
        "sigma_skill": skill,
        "catch_rate": catch,
        "fix_rate": fix,
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
# Reviewer detects (catch_rate) but the corrector only repairs a fraction
# (fix_rate < 1). Exercises the detection × fix-success generalization of Eq. 6.
PIPE_FIX = {
    "nodes": [
        _nd("gen", 0.62, 0.70, [], fix=0.5),
        _nd("review_correct", 0.80, 0.65, ["gen"], fix=0.8),
    ]
}
# Allocation-optimizer fixtures (mso-optimize.js ↔ optimize.py).
OPT_NODES_A = [
    {"id": "draft", "role": "generator", "task": "drafting",
     "complexity": "moderate", "model": "qwen3-8b", "parents": []},
]
OPT_NODES_B = [
    {"id": "a", "role": "generator", "task": "drafting", "complexity": "easy",
     "model": "claude-opus-4", "parents": []},
    {"id": "b", "role": "reviewer", "task": "review", "complexity": "easy",
     "model": "claude-opus-4", "parents": ["a"]},
]

CASES = {
    "fisher": SIGMAS,
    "volume": SIGMAS,
    "sraw_fp": [[0.55, 10, 2, 0], [0.8, 10, 2, 0], [0.45, 10, 2, 0.1], [0.62, 8, 3, 0]],
    "scorr": [
        [0.5167, 0.65], [0.375, 0.70], [0.708, 0.70], [0.2, 0.9],
        # 3-arg form: fix_rate < 1 (corrector repairs only a fraction of catches)
        [0.5167, 0.65, 0.5], [0.375, 0.70, 0.8], [0.2, 0.9, 1.0], [0.6, 0.5, 0.0],
    ],
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
        {"pipeline": PIPE_FIX, "p_min": 0.70, "hw": 0.0},
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
    # mso-priors.js seeds a node from (model × task) benchmark priors.
    # Covers generator branch (sigma_skill) and review branch (catch_rate).
    "seed_node": [
        {"model": "claude-opus-4", "task_type": "code_generation"},
        {"model": "gpt-4o", "task_type": "drafting"},
        {"model": "gemini-2-flash", "task_type": "review"},
        {"model": "deepseek-r1", "task_type": "extraction"},
        # v2 component types: embedder retrieval, reranker, judge, corrector
        {"model": "qwen3-embedding-8b", "task_type": "retrieval"},
        {"model": "rankgpt-gpt4", "task_type": "reranking"},
        {"model": "llm-judge-ensemble", "task_type": "review"},
        {"model": "corrector-with-feedback", "task_type": "correction"},
        {"model": "gpt-5.4-nano", "task_type": "grounded_generation"},
    ],
    # mso-registry.js / mso-optimize.js — the cost-aware allocation layer.
    "opt_registry": [
        {"model": "gpt-4o", "in": 2000, "out": 500},
        {"model": "phi-4", "in": 1500, "out": 400},
        {"model": "claude-opus-4", "in": 1000, "out": 1000},
        {"model": "fable-5", "in": 1000, "out": 100},
    ],
    "opt_eff": [
        {"prior": 0.90, "complexity": "easy", "misuse": 0.0},
        {"prior": 0.90, "complexity": "critical", "misuse": 0.0},
        {"prior": 0.90, "complexity": "moderate", "misuse": 0.25},
    ],
    "opt_eval": [
        {"nodes": OPT_NODES_A, "p_min": 0.80, "budget": None},
        {"nodes": OPT_NODES_B, "p_min": 0.80, "budget": None},
    ],
    "opt_candidates": [
        {"task": "drafting", "complexity": "easy", "misuse": 0, "target": 0.85},
        {"task": "review", "complexity": "moderate", "misuse": 0, "target": 0.0},
    ],
    "opt_alloc": [
        {"nodes": OPT_NODES_A, "p_min": 0.80, "budget": None},
        {"nodes": OPT_NODES_B, "p_min": 0.80, "budget": 0.03},
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
            fix_rate=n.get("fix_rate"),
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
        fix = n.get("fix_rate")
        fix = 1.0 if fix is None else fix
        lsr = F.sigma_raw_fixed_point(n["sigma_skill"], 10, 2, 0)
        lsc = F.sigma_corr_fixed_point(lsr, n["catch_rate"], fix)
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
    exp["seed_node"] = []
    for c in CASES["seed_node"]:
        s = P.seed_node(c["model"], c["task_type"])
        prov = s["provenance"]
        exp["seed_node"].append({
            "seeds": s["seeds"],
            "sigma_skill": s.get("sigma_skill"),
            "catch_rate": s.get("catch_rate"),
            "fix_rate": s.get("fix_rate"),
            "confidence": prov["confidence"],
            "band_low": prov["band"]["low"],
            "band_mid": prov["band"]["mid"],
            "band_high": prov["band"]["high"],
        })

    exp["opt_registry"] = []
    for c in CASES["opt_registry"]:
        exp["opt_registry"].append({
            "cost": REG.cost_per_run(c["model"], c["in"], c["out"]),
            "blended": REG.blended_cost(c["model"]),
            "index": REG.get_model(c["model"]).cost_index,
            "open": REG.is_open_source(c["model"]),
        })
    exp["opt_eff"] = [_eff(c["prior"], c["complexity"], c.get("misuse", 0))
                      for c in CASES["opt_eff"]]
    exp["opt_eval"] = []
    for c in CASES["opt_eval"]:
        e = OPT.evaluate(c["nodes"], c["p_min"], c["budget"])
        exp["opt_eval"].append({"c_op": e.c_op, "cost": e.cost, "feasible": e.feasible})
    exp["opt_candidates"] = [
        [o.model for o in OPT.candidate_models(c["task"], c["complexity"],
                                               c.get("misuse", 0), c.get("target", 0))]
        for c in CASES["opt_candidates"]
    ]
    exp["opt_alloc"] = []
    for c in CASES["opt_alloc"]:
        r = OPT.optimize_allocation(c["nodes"], c["p_min"], budget=c["budget"], prefer_oss=True)
        exp["opt_alloc"].append({
            "c_op": r.c_op, "cost": r.cost, "feasible": r.feasible,
            "within": r.within_budget, "steps": r.steps,
            "models": [n["id"] + ":" + (n.get("model") or "")
                       + ("+ov:" + n["oversight_model"] if n.get("oversight_model") else "")
                       for n in r.nodes],
        })
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

    for i, (g, e) in enumerate(zip(got["seed_node"], exp["seed_node"])):
        c = CASES["seed_node"][i]
        label = f"{c['model']}|{c['task_type']}"
        assert g["seeds"] == e["seeds"], f"seed_node seeds mismatch for {label}"
        for k in ["band_low", "band_mid", "band_high", "confidence"]:
            assert _close(g[k], e[k]), f"seed_node {k} mismatch for {label}"
        for k in ["sigma_skill", "catch_rate", "fix_rate"]:
            if e[k] is not None:
                assert g[k] is not None and _close(g[k], e[k]), f"seed_node {k} mismatch for {label}"
            else:
                assert g[k] is None, f"seed_node {k} should be null for {label}"

    # --- cost-aware allocation parity (mso-registry.js / mso-optimize.js) ---
    for g, e in zip(got["opt_registry"], exp["opt_registry"]):
        assert g["open"] == e["open"], "registry open flag mismatch"
        assert g["index"] == e["index"], "registry cost_index mismatch"
        for k in ["cost", "blended"]:
            if e[k] is None:
                assert g[k] is None, f"registry {k} should be null"
            else:
                assert _close(g[k], e[k]), f"registry {k} mismatch"

    for g, e in zip(got["opt_eff"], exp["opt_eff"]):
        assert _close(g, e), "effective_sigma mismatch"

    for g, e in zip(got["opt_eval"], exp["opt_eval"]):
        assert g["feasible"] == e["feasible"], "evaluate feasible mismatch"
        for k in ["c_op", "cost"]:
            assert _close(g[k], e[k]), f"evaluate {k} mismatch"

    for g, e in zip(got["opt_candidates"], exp["opt_candidates"]):
        assert g == e, f"candidate_models order mismatch:\n  js={g}\n  py={e}"

    for g, e in zip(got["opt_alloc"], exp["opt_alloc"]):
        assert g["feasible"] == e["feasible"], "optimize feasible mismatch"
        assert g["within"] == e["within"], "optimize within_budget mismatch"
        assert g["steps"] == e["steps"], f"optimize steps mismatch:\n  js={g['steps']}\n  py={e['steps']}"
        assert g["models"] == e["models"], f"optimize final models mismatch:\n  js={g['models']}\n  py={e['models']}"
        for k in ["c_op", "cost"]:
            assert _close(g[k], e[k]), f"optimize {k} mismatch"
