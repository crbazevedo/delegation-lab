# Interactive companion

The repository ships a dependency-free, embeddable widget suite under
[`web/`](https://github.com/crbazevedo/delegation-lab/tree/main/web) that
computes the paper's quantities **live in the browser** — the same equations as
this package, validated against it.

## Run it locally

No build step required:

```bash
cd web && python -m http.server 8000   # then open http://localhost:8000
```

## The widgets

| Widget | Demonstrates |
|--------|--------------|
| **Governance cockpit** | Build or load a delegated workflow from a connector library (HubSpot, Salesforce, GitHub, Jira, Slack, LLM, human review…), edit the graph, and read feasibility (`C_op`), the bottleneck, masking, motifs, delegation centrality, and risk off it live. Includes merge gates, review loops, didactic lessons, and a **Run** mode that animates task tokens through the graph. |
| **Feasibility & oversight cockpit** | `C_op` vs `p_min`, autonomy buffer `B_eff`, capacity cliff `H_crit`, per-node masking. |
| **The masking pathology** | `M* = σ_corr/σ_raw`, reproducing the paper's `M*=1.83`. |
| **Water-filling oversight** | The Euler–Lagrange allocation `α*(x)` at least cost. |
| **The Return Operator, run on time** | The competence ODE `dσ/dt = η(σ_skill,eff − σ) − δ(σ − σ₀)` integrated forward: `σ_raw` drifts, `σ_corr` holds, masking widens; intervene to reset the autonomy window. |
| **Token simulation (stochastic Petri net)** | Tasks as tokens flowing through the pipeline with real review loops; empirical end-to-end success converging to the analytic `C_op`. |
| **Water-filling vs the baseline paradigm** | MSO vs uniform oversight at equal delivery, plus endogenous task allocation (scope selection); the advantage grows with task heterogeneity. |

## Grounding guarantee

Two browser modules sit on top of the package:

- `web/mso-core.js` — a faithful port of the closed forms in
  `minimal_oversight._formulae` (plus capacity propagation, topology, and
  allocation). It is pinned to the Python package by `tests/test_parity.py`:
  every formula, plus end-to-end pipeline capacity, bottleneck identity, the
  Return-Operator trajectory, motif descriptions, delegation centrality, risk
  ranking, and scope selection, must agree to within `1e-6`.
- `web/mso-sim.js` — a lightweight stochastic-Petri-net token simulator. It is
  validated by `tests/test_sim_grounding.py`: the empirical end-to-end success
  from many tokens lands within `0.02` of the closed-form `C_op` (the discrete
  Petri-net level and the mean-field MSO level agree).

```bash
python -m pytest tests/test_parity.py tests/test_sim_grounding.py -q
```

The parity tests run in CI (Node is available on the runners), so the widgets
cannot silently drift from the package or the paper.

## Embed a widget

Each widget is one HTML file plus two shared assets (`mso-core.js`,
`theme.css`). Or load the core directly:

```html
<script src="mso-core.js"></script>
<script>
  const r = MSO.analyzePipeline({ nodes: [
    { id: "gen", sigma_skill: 0.55, catch_rate: 0.70, parents: [] },
    { id: "rev", sigma_skill: 0.60, catch_rate: 0.70, parents: ["gen"] },
  ]}, { p_min: 0.80 });
  console.log(r.cop, r.bottleneck, r.perNode.gen.masking); // matches analyze_pipeline()
</script>
```
