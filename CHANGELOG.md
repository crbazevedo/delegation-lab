# Changelog

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
