"""Smoke test: build an SDLC pipeline and run analyze_pipeline()."""

from minimal_oversight import analyze_pipeline
from minimal_oversight.models import AggregationType, Node, PipelineGraph
from minimal_oversight.simulation import generate_synthetic_traces


def make_sdlc_pipeline() -> PipelineGraph:
    """The paper's SDLC pipeline: gen → review → {test, req, sec} → merge."""
    gen = Node("generator", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50)
    rev = Node("reviewer", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50)
    test = Node("test", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50)
    req = Node("requirements", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50)
    sec = Node("security", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50)
    merge = Node(
        "merge", sigma_skill=0.55, catch_rate=0.65, review_capacity=0.50,
        aggregation=AggregationType.PRODUCT,
    )

    pipeline = PipelineGraph([gen, rev, test, req, sec, merge])
    pipeline.add_edge("generator", "reviewer")
    pipeline.add_edge("reviewer", "test")
    pipeline.add_edge("reviewer", "requirements")
    pipeline.add_edge("reviewer", "security")
    pipeline.add_edge("test", "merge")
    pipeline.add_edge("requirements", "merge")
    pipeline.add_edge("security", "merge")
    return pipeline


def test_analyze_pipeline_runs():
    """analyze_pipeline() should complete without errors and return a report."""
    pipeline = make_sdlc_pipeline()
    report = analyze_pipeline(pipeline, p_min=0.50)

    assert report.feasibility is not None
    assert report.feasibility.c_op > 0
    assert len(report.motifs) > 0
    assert len(report.recommendations) > 0
    assert str(report)  # __str__ should work


def test_analyze_with_traces():
    """analyze_pipeline() with synthetic traces."""
    pipeline = make_sdlc_pipeline()
    traces = generate_synthetic_traces(pipeline, n_items=200, seed=42)
    report = analyze_pipeline(pipeline, p_min=0.50, traces=traces)

    assert len(report.node_estimates) == 6
    for est in report.node_estimates.values():
        assert 0 < est.sigma_raw <= 1
        assert 0 < est.sigma_corr <= 1
        assert est.sample_size > 0


def test_report_str():
    """The report should produce readable output."""
    pipeline = make_sdlc_pipeline()
    report = analyze_pipeline(pipeline, p_min=0.50)
    output = str(report)
    assert "PIPELINE ANALYSIS REPORT" in output
    assert "Feasibility" in output
