# Interactive companion widgets

Three dependency-free browser widgets that demonstrate the **Minimum Sufficient
Oversight Principle (MSO)** from the paper, computed live by the same equations
as the `minimal-oversight` package.

| File | Demonstrates |
|------|--------------|
| `widgets/feasibility.html` | Feasibility ceiling `C_op`, bottleneck, autonomy buffer `B_eff`, capacity cliff `H_crit`, per-node masking |
| `widgets/masking.html` | Masking pathology `M* = σ_corr/σ_raw` (reproduces the paper's M*=1.83) |
| `widgets/waterfilling.html` | Euler-Lagrange oversight allocation `α*(x)` at least cost |
| `mso-core.js` | Browser port of `minimal_oversight._formulae` + capacity propagation |
| `theme.css` | Self-contained light/dark theme (no build step) |

## Grounding guarantee

`mso-core.js` is a faithful re-implementation of the paper's closed forms.
`tests/test_parity.py` runs the same inputs through **both** the Python package
and `mso-core.js` (via Node) and asserts agreement to within `1e-6` — covering
every formula plus end-to-end pipeline capacity, bottleneck identity, and
feasibility verdict. The widgets therefore cannot silently drift from the paper.

```bash
# from the repo root, with the package installed and Node available
python -m pytest tests/test_parity.py -q
```

## Run locally

No server required — open `web/index.html` in a browser, or:

```bash
cd web && python -m http.server 8000   # then visit http://localhost:8000
```

## Embed in another page

Each widget is one HTML file plus two shared assets. Copy `mso-core.js` and
`theme.css` alongside the widget, or load `mso-core.js` directly and call it:

```html
<script src="mso-core.js"></script>
<script>
  const r = MSO.analyzePipeline({ nodes: [
    { id: "gen", sigma_skill: 0.55, catch_rate: 0.70, parents: [] },
    { id: "rev", sigma_skill: 0.60, catch_rate: 0.70, parents: ["gen"] },
  ]}, { p_min: 0.80 });
  console.log(r.cop, r.bottleneck, r.perNode.gen.masking); // → matches analyze_pipeline()
</script>
```

`mso-core.js` is UMD-style: it exposes `window.MSO` in the browser and
`module.exports` under Node, so the same file powers the widgets and the
parity runner.
