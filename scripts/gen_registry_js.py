#!/usr/bin/env python3
"""Generate web/mso-registry.js from src/minimal_oversight/data/model_registry.yaml.

The YAML is the single source of truth. This loads it through the package's
(index-deriving) loader and emits the browser bundle, so the cockpit's cost +
license data can never drift from the Python registry.

Usage:  python scripts/gen_registry_js.py [--check]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from minimal_oversight import registry as R  # noqa: E402

OUT = REPO / "web" / "mso-registry.js"


def _num(x):
    return "null" if x is None else json.dumps(round(float(x), 6))


def build() -> str:
    data = R.load_registry()
    models = data["models"]
    lines = []
    for name in sorted(models):
        m = models[name]
        obj = (
            "{provider:" + json.dumps(m.provider)
            + ",modality:" + json.dumps(m.modality)
            + ",license:" + json.dumps(m.license_name)
            + ",open:" + ("true" if m.open else "false")
            + ",input:" + _num(m.input_usd_per_mtok)
            + ",output:" + _num(m.output_usd_per_mtok)
            + ",blended:" + _num(m.blended_usd_per_mtok)
            + ",cost_index:" + _num(m.cost_index)
            + "}"
        )
        lines.append("  " + json.dumps(name) + ": " + obj + ",")
    block = "\n".join(lines)

    return f'''/**
 * mso-registry.js — model cost + license registry for the allocation optimizer.
 *
 * GENERATED FROM src/minimal_oversight/data/model_registry.yaml — DO NOT EDIT.
 * Regenerate with:  python scripts/gen_registry_js.py
 *
 * cost = USD per million tokens (input/output). blended = 0.6*in + 0.4*out.
 * cost_index = 1..100 log-scale. open = open-weights AND commercially usable.
 * Provenance: docs/methodology/priors-evidence.md (GAP 6).
 */
(function (root, factory) {{
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.MSO_Registry = factory();
}})(typeof self !== "undefined" ? self : this, function () {{
  "use strict";

  var MODELS = {{
{block}
  }};

  function has(name) {{ return !!MODELS[name]; }}
  function get(name) {{ return MODELS[name] || null; }}
  function listModels() {{ return Object.keys(MODELS).sort(); }}
  function isOpenSource(name) {{ var m = MODELS[name]; return !!(m && m.open); }}
  function blendedCost(name) {{ var m = MODELS[name]; return m ? m.blended : null; }}
  function costIndex(name) {{ var m = MODELS[name]; return m ? m.cost_index : null; }}

  // USD per invocation given token volumes. null for an unpriced model.
  function costPerRun(name, inputTokens, outputTokens) {{
    var m = MODELS[name];
    if (!m || m.input == null || m.output == null) return null;
    outputTokens = outputTokens || 0;
    return (inputTokens * m.input + outputTokens * m.output) / 1000000.0;
  }}

  function modelsByModality(modality) {{
    return Object.keys(MODELS).filter(function (n) {{
      return MODELS[n].modality === modality;
    }}).sort();
  }}

  function openModels() {{
    return Object.keys(MODELS).filter(function (n) {{ return MODELS[n].open; }}).sort();
  }}

  return {{
    has: has, get: get, listModels: listModels, isOpenSource: isOpenSource,
    blendedCost: blendedCost, costIndex: costIndex, costPerRun: costPerRun,
    modelsByModality: modelsByModality, openModels: openModels
  }};
}});
'''


def main() -> int:
    generated = build()
    if "--check" in sys.argv:
        current = OUT.read_text() if OUT.exists() else ""
        if current != generated:
            print(f"DRIFT: {OUT} is stale. Run: python scripts/gen_registry_js.py")
            return 1
        print(f"OK: {OUT} matches model_registry.yaml")
        return 0
    OUT.write_text(generated)
    print(f"wrote {OUT} ({generated.count(': {provider:')} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
