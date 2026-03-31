"""Tests for the canonical schema and role inference."""


from minimal_oversight.connectors._bridge import pipeline_from_normalized, traces_from_normalized
from minimal_oversight.connectors._roles import infer_review_edges, infer_role
from minimal_oversight.schema import (
    NodeRole,
    NormalizedEdge,
    NormalizedNode,
    NormalizedOutcome,
    NormalizedPipeline,
    NormalizedTrace,
    defaults_for_role,
)


class TestRoleInference:
    def test_generator_keywords(self):
        assert infer_role("code_generator", "") == NodeRole.GENERATOR
        assert infer_role("writer", "drafts responses") == NodeRole.GENERATOR

    def test_reviewer_keywords(self):
        assert infer_role("reviewer", "") == NodeRole.REVIEWER
        assert infer_role("qa", "validates output quality") == NodeRole.REVIEWER
        assert infer_role("linter", "") == NodeRole.REVIEWER
        assert infer_role("security_check", "") == NodeRole.REVIEWER

    def test_router_keywords(self):
        assert infer_role("triage", "") == NodeRole.ROUTER
        assert infer_role("classifier", "routes to correct handler") == NodeRole.ROUTER

    def test_gate_keywords(self):
        assert infer_role("merge_gate", "") == NodeRole.GATE
        assert infer_role("aggregator", "") == NodeRole.GATE

    def test_human_keywords(self):
        assert infer_role("human_agent", "") == NodeRole.HUMAN
        assert infer_role("escalation", "manual override") == NodeRole.HUMAN
        # "human_review" is ambiguous — head noun "review" wins (REVIEWER),
        # which is the correct head-noun behavior. Use "human_agent" for
        # unambiguous human nodes.

    def test_tool_keywords(self):
        assert infer_role("search_tool", "") == NodeRole.TOOL
        assert infer_role("api_caller", "fetches data") == NodeRole.TOOL

    def test_unknown_fallback(self):
        assert infer_role("xyzzy", "") == NodeRole.UNKNOWN

    def test_description_overrides_name(self):
        # Name is generic but description says reviewer
        assert infer_role("node_3", "reviews and validates output") == NodeRole.REVIEWER

    def test_head_noun_wins_in_compound_names(self):
        # "test_generator" is a generator, not a tester
        assert infer_role("test_generator", "") == NodeRole.GENERATOR
        # "review_generator" is a generator, not a reviewer
        assert infer_role("review_generator", "") == NodeRole.GENERATOR
        # "code_reviewer" is a reviewer, not a generator
        assert infer_role("code_reviewer", "") == NodeRole.REVIEWER
        # "security_checker" is a reviewer (checker is the head noun)
        assert infer_role("security_checker", "") == NodeRole.REVIEWER

    def test_compound_names_with_routing(self):
        # "test_router" is a router, not a tester
        assert infer_role("test_router", "") == NodeRole.ROUTER
        # "check_routing" is a router
        assert infer_role("check_routing", "") == NodeRole.ROUTER


class TestRoleDefaults:
    def test_all_roles_have_defaults(self):
        for role in NodeRole:
            defaults = defaults_for_role(role)
            assert "sigma_skill" in defaults
            assert "catch_rate" in defaults
            assert "review_capacity" in defaults

    def test_human_has_high_catch_rate(self):
        d = defaults_for_role(NodeRole.HUMAN)
        assert d["catch_rate"] >= 0.90

    def test_reviewer_has_higher_skill_than_generator(self):
        gen = defaults_for_role(NodeRole.GENERATOR)
        rev = defaults_for_role(NodeRole.REVIEWER)
        assert rev["sigma_skill"] >= gen["sigma_skill"]


class TestBridge:
    def test_pipeline_from_normalized(self):
        nodes = [
            NormalizedNode(id="gen", name="generator", role=NodeRole.GENERATOR),
            NormalizedNode(id="rev", name="reviewer", role=NodeRole.REVIEWER),
        ]
        edges = [NormalizedEdge(source_id="gen", target_id="rev")]
        norm = NormalizedPipeline(nodes=nodes, edges=edges, framework_source="test")

        pipeline = pipeline_from_normalized(norm)
        assert len(pipeline.nodes) == 2
        assert pipeline.children("gen") == ["rev"]
        # Generator should have default sigma_skill=0.55
        assert pipeline.get_node("gen").sigma_skill == 0.55
        # Reviewer should have default sigma_skill=0.60
        assert pipeline.get_node("rev").sigma_skill == 0.60

    def test_parameter_overrides(self):
        nodes = [NormalizedNode(id="gen", name="gen", role=NodeRole.GENERATOR)]
        norm = NormalizedPipeline(nodes=nodes, edges=[])
        overrides = {"gen": {"sigma_skill": 0.90, "catch_rate": 0.80}}

        pipeline = pipeline_from_normalized(norm, parameter_overrides=overrides)
        assert pipeline.get_node("gen").sigma_skill == 0.90
        assert pipeline.get_node("gen").catch_rate == 0.80

    def test_traces_from_normalized(self):
        outcomes = [
            NormalizedOutcome(task_id="t1", node_id="gen", raw_outcome=1.0, corrected_outcome=1.0),
            NormalizedOutcome(task_id="t1", node_id="rev", raw_outcome=0.0, corrected_outcome=1.0,
                              was_reviewed=True),
            NormalizedOutcome(task_id="t2", node_id="gen", raw_outcome=1.0, corrected_outcome=1.0),
        ]
        norm_traces = [NormalizedTrace(trace_id="tr1", outcomes=outcomes)]

        traces = traces_from_normalized(norm_traces)
        assert len(traces) == 2  # two task_ids
        t1 = next(t for t in traces if t.task_id == "t1")
        assert t1.node_outcomes["gen"] == 1.0
        assert t1.node_outcomes["rev"] == 0.0
        assert t1.node_corrected["rev"] == 1.0


class TestReviewEdgeInference:
    def test_identifies_review_edges(self):
        nodes = [
            ("gen", NodeRole.GENERATOR),
            ("rev", NodeRole.REVIEWER),
            ("merge", NodeRole.GATE),
        ]
        edges = [("gen", "rev"), ("rev", "merge")]
        review = infer_review_edges(nodes, edges)
        assert ("gen", "rev") in review
        assert ("rev", "merge") not in review
