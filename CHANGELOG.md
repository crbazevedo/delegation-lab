# Changelog

## 0.1.3 (2026-06-16)

Interactive companion + grounding harness. No changes to the importable Python
API — `analyze_pipeline()` and friends are unchanged from 0.1.2.

### Added
- **Interactive companion widgets** (`web/`): a dependency-free, embeddable suite
  that computes the paper's quantities live in the browser — a governance cockpit
  (build/edit a delegated workflow from a connector library; read feasibility,
  masking, motifs, delegation centrality, and risk off it), plus focused
  explainers for feasibility, masking (M\*=1.83), water-filling allocation, the
  Return Operator run on time, a stochastic-Petri-net token simulation, and a
  water-filling-vs-baseline benchmark.
- **`web/mso-core.js`**: a faithful browser port of `minimal_oversight._formulae`
  (Fisher info, return-operator fixed points and ODE step, water-filling +
  `solve_lambda`, capacity propagation, masking, motif detection, delegation
  centrality, SOTA score, scope selection).
- **`web/mso-sim.js`**: a lightweight stochastic-Petri-net token simulator
  (tasks as tokens, review loops as real back-arcs).
- **Grounding tests** (`tests/test_parity.py`, `tests/test_sim_grounding.py`):
  pin every ported equation to the Python package to within 1e-6, and assert the
  token simulator's empirical end-to-end success matches the analytic `C_op`.

### Documentation
- Add an "Interactive companion" guide and link it from the README and docs site.
- Clarify MSO as a constrained oversight-allocation principle for delegated AI
  pipelines across README and documentation.

## 0.1.2 (2026-06-04)

Terminology alignment for the revised paper and documentation.

### Core
- Rename the preferred oversight-allocation API to `solve_mso()` for the
  Minimum Sufficient Oversight Principle.
- Keep `solve_amo()` as a backward-compatible alias for existing notebooks and
  user code.

### Documentation
- Replace "Axiom of Minimal Oversight" terminology with "Minimum Sufficient
  Oversight Principle (MSO)" across README, concepts, API docs, and the
  equation-to-code reference.
- Update examples and visualization internals to use `solve_mso()`.

### Tests
- Add regression coverage confirming `solve_mso()` and the legacy `solve_amo()`
  alias return identical allocation results.

## 0.1.1 (2026-06-04)

Equation and documentation alignment for the revised arXiv submission.

### Core
- Add the prior-aware Return Operator with `sigma_0` support in fixed-point,
  simulation, capacity, and one-call analysis paths.
- Make channel-capacity calculation explicit about revealed versus hidden
  review/action logs.
- Compute maximum pipeline depth from recursive corrected-chain quality rather
  than the older product approximation.
- Use raw fixed-point support in corrector-capacity thresholds and clamp
  already-feasible thresholds to zero.

### Documentation
- Reframe package language around uncertainty-aware governed delegation and
  trust calibration for delegated AI systems.
- Update equation-to-code references, capacity notes, autonomy-time wording, and
  simulation assumptions to match the revised paper.
- Tone down infeasibility claims to the fixed model, topology, and budget.

### Tests
- Add regression coverage for nonzero `sigma_0`, revealed/hidden channel
  capacity, recursive depth limits, and review-capacity thresholds.

## 0.1.0 (2026-03-30)

Initial release.

### Core
- `analyze_pipeline()` flagship API — one call, full governance report
- 7 public modules: models, estimation, capacity, topology, allocation, intervention, viz
- Private `_formulae.py` implementing all numbered equations from the paper
- Subordinate `simulation.py` for what-if analysis

### Framework connectors
- LangGraph: import from `StateGraph` / `CompiledStateGraph` with role inference
- Google ADK: import from `Agent` objects or dict configs with hierarchical IDs
- Trace parsers: LangSmith, ADK session logs, generic JSON events
- Canonical schema (`schema.py`) as stable contract between connectors and analytics
- Auto-detection: `analyze_pipeline()` accepts framework objects directly

### Documentation
- 5 concept pages (paper companion): delegation, masking, capacity, autonomy, topology
- 5 practical guides: analyze, LangGraph, ADK, traces, report interpretation
- Equation-to-code reference mapping every paper equation to its implementation
- 7 curated API reference pages
- Paper validation notebook reproducing all 8 experiments from Section 3

### Notebooks
1. SDLC pipeline (generator → reviewer → {test, req, sec} → merge)
2. Customer-support escalation workflow
3. Topology stress test (chain vs fan-out vs diamond)
4. LangGraph integration (real `StateGraph` + conditional edges)
5. ADK integration (real `Agent` objects + session logs)
6. Paper validation (8 experiments + Table 7)

### Tests
- 69 tests covering formulae, smoke tests, schema, connectors, role inference
- Real LangGraph integration test (`pytest.importorskip`)
