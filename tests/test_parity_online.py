"""Parity test: the online browser port (web/adaptive-online.js) must equal the Python
reference for the online review-control variants.

Pins web/adaptive-online.js to:
  * minimal_oversight.skirental / tracking / caching   (the importable modules), and
  * scripts/online_skirental.py                        (the full-instance simulation).

Both sides compute from the SAME inputs at test time and must agree to within 1e-6
(integer miss counts must agree exactly). Only DETERMINISTIC quantities are pinned —
MARKER eviction is randomized and not NumPy-compatible, so it is left to adaptive-online's
own bound checks.

Skipped automatically when Node.js is unavailable.
"""

from __future__ import annotations

import importlib.util
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest

from minimal_oversight import caching as CA
from minimal_oversight import skirental as SK
from minimal_oversight import tracking as TR

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts" / "parity_runner_online.js"
TOL = 1e-6

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="Node.js not available; parity test requires node",
)

# Full-instance ski-rental forms live in the script, not the importable package.
_spec = importlib.util.spec_from_file_location(
    "online_skirental", REPO / "scripts" / "online_skirental.py"
)
OSK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(OSK)


# --- Shared inputs (both sides compute outputs from these) ---
SK_LAM = [1, 5, 10, 20]
SLACK = [{"tau": 8, "lam": 10}, {"tau": 20, "lam": 10}, {"tau": 40, "lam": 10}, {"tau": 5, "lam": 5}]
DWELL_SLACK = [
    {"tau": 40, "lam": 10, "d": 20},
    {"tau": 10, "lam": 10, "d": 20},
    {"tau": 100, "lam": 5, "d": 8},
]
WORST = [
    {"d": 20, "lam": 10, "tau_max": 1000},
    {"d": 5, "lam": 10, "tau_max": 1000},
    {"d": 40, "lam": 10, "tau_max": 1000},
]
MINIMAX = [{"lam": 1}, {"lam": 5}, {"lam": 10}, {"lam": 20}]
INSTANCE = [
    {"W": 1, "tau": 320, "lam": 10, "ncyc": 20, "d": 20},  # the hero operating point (CR 14.92 / 1.88)
    {"W": 1, "tau": 40, "lam": 10, "ncyc": 30, "d": 20},
    {"W": 1, "tau": 8, "lam": 10, "ncyc": 10, "d": 20},
    {"W": 2, "tau": 60, "lam": 5, "ncyc": 15, "d": 10},
]
TRACKING = [
    {"nu": 0.02, "sigma": 0.20},
    {"nu": 0.01, "sigma": 0.40},
    {"nu": 0.04, "sigma": 0.10},
    {"nu": 0.05, "sigma": 1.0},
]
_OBS = [round(math.sin(i * 0.3) + 0.01 * i, 6) for i in range(30)]  # deterministic, shared
KALMAN_SEQ = [{"nu": 0.02, "sigma": 0.20, "xhat": 0.0, "obs": _OBS}]
POOL = [{"c": 2.0, "b": 1.0}, {"c": 5.0, "b": 2.0}, {"c": 8.0, "b": 1.0}]
CYCLIC = [{"h": 2, "rounds": 50}, {"h": 8, "rounds": 20}]


def _requests():
    reqs = []
    for h, rounds in [(2, 50), (3, 40), (4, 30), (8, 20)]:
        reqs.append({"req": CA.cyclic_adversary(h, rounds), "h": h})
    rng = np.random.default_rng(0)
    reqs.append({"req": [int(x) for x in rng.integers(0, 7, size=200)], "h": 3})
    return reqs


REQS = _requests()

CASES = {
    "sk_lam": SK_LAM,
    "slack": SLACK,
    "dwell_slack": DWELL_SLACK,
    "worst": WORST,
    "minimax": MINIMAX,
    "instance": INSTANCE,
    "tracking": TRACKING,
    "kalman_seq": KALMAN_SEQ,
    "pool": POOL,
    "requests": REQS,
    "cyclic": CYCLIC,
}


def _expected() -> dict:
    exp: dict = {}
    exp["sk_dwell"] = [SK.skirental_dwell(lam) for lam in SK_LAM]
    exp["sk_ratio"] = [SK.skirental_ratio(lam) for lam in SK_LAM]
    exp["opt_slack"] = [SK.opt_slack_cost(a["tau"], a["lam"]) for a in SLACK]
    exp["dwell_slack"] = [SK.dwell_slack_cost(a["tau"], a["lam"], a["d"]) for a in DWELL_SLACK]
    exp["worst_case"] = [SK.worst_case_ratio(a["d"], a["lam"], a["tau_max"]) for a in WORST]
    exp["minimax"] = []
    for a in MINIMAX:
        d, r = SK.minimax_dwell(a["lam"])
        exp["minimax"].append({"dwell": d, "ratio": r})
    exp["opt_cost"] = [OSK.opt_cost(a["W"], a["tau"], a["lam"], a["ncyc"]) for a in INSTANCE]
    exp["dwell_cost"] = [OSK.dwell_cost(a["W"], a["tau"], a["lam"], a["ncyc"], a["d"]) for a in INSTANCE]
    exp["cr_ratchet"] = [OSK.cr("ratchet", a["W"], a["tau"], a["lam"], a["ncyc"]) for a in INSTANCE]
    exp["cr_dwell"] = [OSK.cr("dwell", a["W"], a["tau"], a["lam"], a["ncyc"], dwell=a["d"]) for a in INSTANCE]
    exp["kal_var"] = [TR.kalman_steadystate_var(a["nu"], a["sigma"]) for a in TRACKING]
    exp["matched"] = [TR.matched_margin(TR.kalman_steadystate_var(a["nu"], a["sigma"])) for a in TRACKING]
    exp["floor"] = [TR.noise_floor_per_step(a["nu"], a["sigma"]) for a in TRACKING]
    exp["deadband"] = [TR.deadband_margin(a["sigma"]) for a in TRACKING]
    exp["kal_track"] = []
    for c in KALMAN_SEQ:
        kt = TR.KalmanTracker(c["nu"], c["sigma"], xhat=c["xhat"])
        exp["kal_track"].append([kt.update(o) for o in c["obs"]])
    exp["pool_cap"] = [CA.pool_capacity(a["c"], a["b"]) for a in POOL]
    exp["lru"] = [CA.lru_misses(rq["req"], rq["h"]) for rq in REQS]
    exp["belady"] = [CA.belady_misses(rq["req"], rq["h"]) for rq in REQS]
    exp["ratchet_demand"] = [CA.ratchet_demand(rq["req"]) for rq in REQS]
    exp["cr_lru"] = [CA.competitive_ratio("lru", rq["req"], rq["h"]) for rq in REQS]
    exp["cyclic_len"] = [len(CA.cyclic_adversary(a["h"], a["rounds"])) for a in CYCLIC]
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


def test_online_browser_port_matches_python_reference():
    got = _run_node(CASES)
    exp = _expected()

    # scalar / vector closed forms — agree to 1e-6
    for key in [
        "sk_dwell", "sk_ratio", "opt_slack", "dwell_slack", "worst_case",
        "opt_cost", "dwell_cost", "cr_ratchet", "cr_dwell",
        "kal_var", "matched", "floor", "deadband", "cr_lru",
    ]:
        assert _close(got[key], exp[key]), f"mismatch in {key}:\n  js={got[key]}\n  py={exp[key]}"

    # minimax returns (dwell*, ratio)
    for g, e in zip(got["minimax"], exp["minimax"]):
        assert _close(g["dwell"], e["dwell"]), "minimax dwell mismatch"
        assert _close(g["ratio"], e["ratio"]), "minimax ratio mismatch"

    # stateful Kalman trajectory on a shared observation sequence
    for g, e in zip(got["kal_track"], exp["kal_track"]):
        assert _close(g, e), "kalman trajectory mismatch"

    # integer counts — must agree exactly
    for key in ["pool_cap", "lru", "belady", "ratchet_demand", "cyclic_len"]:
        assert got[key] == exp[key], f"integer mismatch in {key}:\n  js={got[key]}\n  py={exp[key]}"


def test_hero_operating_point_pins_to_published_anchors():
    """The hero's three on-screen numbers must reproduce the published anchors."""
    # ratchet CR 14.9 at tau=320 (NOT tau=332, which is 15.48); dwell 1.88; bound 1.95.
    assert abs(OSK.cr("ratchet", 1, 320, 10, 20) - 14.9) < 0.05
    assert abs(OSK.cr("ratchet", 1, 332, 10, 20) - 15.48) < 0.05  # the forbidden point
    assert abs(OSK.cr("dwell", 1, 320, 10, 20, dwell=20) - 1.88) < 0.01
    assert abs(SK.skirental_ratio(10) - 1.95) < 1e-9
