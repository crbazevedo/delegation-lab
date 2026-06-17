"""Grounding test: the JS token simulator (web/mso-sim.js) agrees with the
analytic core (and the package's C_op) on end-to-end success.

This is NOT a bit-parity test — the simulator is stochastic and RNG differs
across languages. Instead it asserts the empirical end-to-end success from many
tokens lands within a few percent of the closed-form C_op, validating that the
discrete Stochastic-Petri-Net level and the mean-field MSO level agree.

Skipped automatically when Node.js is unavailable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from minimal_oversight import analyze_pipeline
from minimal_oversight.models import AggregationType, Node, PipelineGraph

REPO = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js not available"
)

_AGG = {
    "product": AggregationType.PRODUCT,
    "min": AggregationType.WEAKEST_LINK,
    "mean": AggregationType.WEIGHTED_MEAN,
}


def _nd(node_id, skill, catch, parents, agg="product"):
    return {
        "id": node_id, "sigma_skill": skill, "catch_rate": catch,
        "review_capacity": 1, "parents": parents, "aggregation": agg,
    }


CHAIN = {"nodes": [
    _nd("a", 0.7, 0.7, []),
    _nd("b", 0.65, 0.7, ["a"]),
    _nd("c", 0.6, 0.7, ["b"]),
]}
DIAMOND = {"nodes": [
    _nd("s", 0.8, 0.6, []),
    _nd("x", 0.6, 0.7, ["s"]),
    _nd("y", 0.6, 0.7, ["s"]),
    _nd("m", 0.75, 0.7, ["x", "y"], "mean"),
]}

RUNNER = """
const SIM = require(process.argv[2] + "/web/mso-sim.js");
const inp = JSON.parse(require("fs").readFileSync(process.argv[3], "utf8"));
const out = inp.map((pipe) => SIM.simulateTokens(pipe, { n: 60000, seed: 11 }).endToEndSuccess);
process.stdout.write(JSON.stringify(out));
"""


def _build(spec):
    nodes = [
        Node(n["id"], sigma_skill=n["sigma_skill"], catch_rate=n["catch_rate"],
             review_capacity=n["review_capacity"], aggregation=_AGG[n["aggregation"]])
        for n in spec["nodes"]
    ]
    g = PipelineGraph(nodes)
    for n in spec["nodes"]:
        for p in n["parents"]:
            g.add_edge(p, n["id"])
    return g


def test_token_sim_matches_analytic_cop():
    pipes = [CHAIN, DIAMOND]
    with tempfile.TemporaryDirectory() as d:
        runner = Path(d) / "run.js"
        runner.write_text(RUNNER)
        inp = Path(d) / "pipes.json"
        inp.write_text(json.dumps(pipes))
        res = subprocess.run(
            ["node", str(runner), str(REPO), str(inp)],
            check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
        empirical = json.loads(res.stdout)

    for spec, emp in zip(pipes, empirical):
        cop = analyze_pipeline(_build(spec), p_min=0.8).feasibility.c_op
        assert abs(emp - cop) < 0.02, f"empirical {emp:.3f} vs analytic C_op {cop:.3f}"
