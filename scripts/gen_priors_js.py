#!/usr/bin/env python3
"""Generate web/mso-priors.js from src/minimal_oversight/data/priors.yaml.

The YAML is the single source of truth. This script loads it through the
package's own (validating) loader and emits the browser bundle, so the cockpit
seeder and the Python reference can never drift. The parity test
(tests/test_parity.py) pins seedNode JS ↔ Python to 1e-9 on top of this.

Usage:  python scripts/gen_priors_js.py [--check]
  (no args) rewrite web/mso-priors.js
  --check   exit 1 if the file on disk differs from freshly-generated output
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from minimal_oversight import priors as P  # noqa: E402

OUT = REPO / "web" / "mso-priors.js"


def _num(x: float) -> str:
    """Compact JS number literal (shortest round-trip, matches JSON.stringify)."""
    return json.dumps(round(float(x), 6))


def _band_for(cell) -> tuple[str, object]:
    """Return (kind, band) — which payload this cell seeds from."""
    if cell.task_type == P.REVIEW_TASK:
        return "review", cell.catch_rate
    if cell.task_type == P.CORRECTION_TASK:
        return "correction", cell.fix_rate
    return "generator", cell.sigma_raw


def build() -> str:
    data = P.load_priors()
    cells = data["cells"]
    models = sorted({m for (m, _t) in cells})
    task_types = list(data["task_types"])

    lines: list[str] = []
    for (model, task) in cells:
        cell = cells[(model, task)]
        kind, band = _band_for(cell)
        obj = (
            "{kind:" + json.dumps(kind)
            + ",band:{low:" + _num(band.low)
            + ",mid:" + _num(band.mid)
            + ",high:" + _num(band.high) + "}"
            + ",benchmark:" + json.dumps(cell.primary_benchmark or "")
            + ",metric_kind:" + json.dumps(cell.metric_kind or "")
            + ",note:" + json.dumps(cell.normalization_note or "")
            + "}"
        )
        lines.append('  ' + json.dumps(model + "|" + task) + ": " + obj + ",")
    cells_block = "\n".join(lines)

    return f'''/**
 * mso-priors.js — cold-start σ_raw / catch_rate / fix_rate priors for cockpit nodes.
 *
 * GENERATED FROM src/minimal_oversight/data/priors.yaml — DO NOT EDIT BY HAND.
 * Regenerate with:  python scripts/gen_priors_js.py
 *
 * Mirrors minimal_oversight.priors.seed_node (Python) exactly:
 *   - generator / retrieval / reranking task-types → sigma_skill = clamp(mid/γ, 0.05, 0.98)
 *     so gamma * sigma_skill == band.mid at the calibration-operator fixed point.
 *   - review task-type → catch_rate = clamp(mid, 0, 1)   (reviewer error-detection)
 *   - correction task-type → fix_rate = clamp(mid, 0, 1)  (corrector repair-success)
 *   - provenance.confidence = 1 − band_width (a crude evidence-strength proxy).
 *
 * Provenance for every band: docs/methodology/priors-evidence.md.
 * Parity: tests/test_parity.py pins JS ↔ Python to within 1e-9 on seedNode outputs.
 */
(function (root, factory) {{
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.MSO_Priors = factory();
}})(typeof self !== "undefined" ? self : this, function () {{
  "use strict";

  var GAMMA = 10 / 12;   // η/(η+δ) calibration-operator fixed-point gain

  function clamp(x, a, b) {{ return Math.max(a, Math.min(b, x)); }}

  // ---- bundled prior table (generated from data/priors.yaml) -----------------
  var CELLS = {{
{cells_block}
  }};

  var MODELS = {json.dumps(models)};
  var TASK_TYPES = {json.dumps(task_types)};

  // ---- public API ------------------------------------------------------------

  /** List all model names in the table. */
  function listModels() {{ return MODELS.slice(); }}

  /** List all task-type names in the table. */
  function listTaskTypes() {{ return TASK_TYPES.slice(); }}

  /** List the task-types that have a prior for the given model. */
  function tasksForModel(model) {{
    return TASK_TYPES.filter(function (t) {{ return !!CELLS[model + "|" + t]; }});
  }}

  /** List the models that have a prior for the given task-type. */
  function modelsForTask(taskType) {{
    return MODELS.filter(function (m) {{ return !!CELLS[m + "|" + taskType]; }});
  }}

  /** Return true if a prior exists for the (model, taskType) pair. */
  function hasCell(model, taskType) {{ return !!(CELLS[model + "|" + taskType]); }}

  /**
   * Seed a cockpit Node from a (model, taskType) prior.
   *
   * Returns an object ready to be merged onto a node:
   *   {{ model, task_type, is_prior: true, seeds, sigma_skill?, catch_rate?, fix_rate?, provenance }}
   *
   * Mirrors Python priors.seed_node exactly. Throws if no cell exists.
   */
  function seedNode(model, taskType) {{
    var cell = CELLS[model + "|" + taskType];
    if (!cell) throw new Error("no prior for model=" + model + " task_type=" + taskType);

    var b = cell.band;
    var out = {{ model: model, task_type: taskType, is_prior: true }};

    if (taskType === "review") {{
      out.catch_rate = clamp(b.mid, 0, 1);
      out.seeds = "catch_rate";
    }} else if (taskType === "correction") {{
      out.fix_rate = clamp(b.mid, 0, 1);
      out.seeds = "fix_rate";
    }} else {{
      out.sigma_skill = clamp(b.mid / GAMMA, 0.05, 0.98);
      out.catch_rate = 0.0;
      out.seeds = "sigma_skill";
    }}

    out.provenance = {{
      band: {{ low: b.low, mid: b.mid, high: b.high }},
      confidence: Math.round((1 - (b.high - b.low)) * 1000) / 1000,
      benchmark: cell.benchmark,
      metric_kind: cell.metric_kind,
      note: cell.note
    }};
    return out;
  }}

  /** The prior band MID for (model, task), or null. Used by the optimizer. */
  function priorMid(model, taskType) {{
    var cell = CELLS[model + "|" + taskType];
    return cell ? cell.band.mid : null;
  }}

  return {{
    listModels: listModels, listTaskTypes: listTaskTypes,
    tasksForModel: tasksForModel, modelsForTask: modelsForTask,
    hasCell: hasCell, seedNode: seedNode, priorMid: priorMid, GAMMA: GAMMA
  }};
}});
'''


def main() -> int:
    generated = build()
    if "--check" in sys.argv:
        current = OUT.read_text() if OUT.exists() else ""
        if current != generated:
            print(f"DRIFT: {OUT} is stale. Run: python scripts/gen_priors_js.py")
            return 1
        print(f"OK: {OUT} matches priors.yaml")
        return 0
    OUT.write_text(generated)
    n = generated.count('": {kind:')
    print(f"wrote {OUT} ({n} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
