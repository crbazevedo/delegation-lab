"""Tests for framework connectors (without requiring actual frameworks installed)."""

import warnings

import pytest

from minimal_oversight import analyze_pipeline
from minimal_oversight.connectors.adk import from_adk_config, normalize_adk_config
from minimal_oversight.connectors.langgraph import normalize_langgraph
from minimal_oversight.connectors.traces import (
    from_adk_session_logs,
    from_generic_events,
    from_langsmith_traces,
    to_workflow_traces,
)
from minimal_oversight.connectors._bridge import traces_from_normalized
from minimal_oversight.schema import EventType, NodeRole, NormalizedOutcome, NormalizedTrace


class TestADKConnector:
    def test_simple_adk_config(self):
        config = {
            "name": "support_agent",
            "description": "Routes customer queries to specialists",
            "model": "gemini-2.0-flash",
            "sub_agents": [
                {
                    "name": "billing_agent",
                    "description": "Handles billing questions",
                    "model": "gemini-2.0-flash",
                },
                {
                    "name": "tech_support",
                    "description": "Resolves technical issues",
                    "model": "gemini-2.0-flash",
                },
            ],
        }
        pipeline = from_adk_config(config)
        assert len(pipeline.nodes) == 3
        # Sub-agent IDs are now hierarchical: parent/child
        assert pipeline.children("support_agent") == [
            "support_agent/billing_agent",
            "support_agent/tech_support",
        ]

    def test_nested_adk_config(self):
        config = {
            "name": "root",
            "sub_agents": [
                {
                    "name": "reviewer",
                    "description": "Reviews generated code",
                    "sub_agents": [
                        {"name": "lint_check", "description": "Runs linting"},
                        {"name": "security_scan", "description": "Security analysis"},
                    ],
                },
            ],
        }
        pipeline = from_adk_config(config)
        assert len(pipeline.nodes) == 4
        # Hierarchical IDs: root/reviewer/lint_check
        assert "root/reviewer/lint_check" in pipeline.children("root/reviewer")

    def test_role_inference_from_config(self):
        config = {
            "name": "orchestrator",
            "sub_agents": [
                {"name": "code_generator", "description": "Writes code"},
                {"name": "code_reviewer", "description": "Reviews code quality"},
                {"name": "security_check", "description": "Validates security"},
            ],
        }
        normalized = normalize_adk_config(config)
        roles = {n.id: n.role for n in normalized.nodes}
        # Sub-agent IDs are hierarchical
        assert roles["orchestrator/code_generator"] == NodeRole.GENERATOR
        assert roles["orchestrator/code_reviewer"] == NodeRole.REVIEWER
        assert roles["orchestrator/security_check"] == NodeRole.REVIEWER

    def test_parameter_overrides(self):
        config = {"name": "agent", "sub_agents": [{"name": "worker"}]}
        # Overrides must use the hierarchical ID
        overrides = {"agent/worker": {"sigma_skill": 0.90}}
        pipeline = from_adk_config(config, parameter_overrides=overrides)
        assert pipeline.get_node("agent/worker").sigma_skill == 0.90

    def test_analyze_adk_config_directly(self):
        """analyze_pipeline() should auto-detect ADK dict configs."""
        config = {
            "name": "root",
            "sub_agents": [
                {"name": "generator", "description": "Writes drafts"},
                {"name": "reviewer", "description": "Reviews drafts"},
            ],
        }
        report = analyze_pipeline(config, p_min=0.50)
        assert report.feasibility is not None
        assert report.feasibility.c_op > 0


class TestGenericTraceParser:
    def test_simple_events(self):
        events = [
            {"task_id": "t1", "node_id": "gen", "outcome": "success", "timestamp": 1.0},
            {"task_id": "t1", "node_id": "rev", "outcome": "failure", "timestamp": 2.0},
            {"task_id": "t2", "node_id": "gen", "outcome": "success", "timestamp": 3.0},
        ]
        traces = from_generic_events(events)
        assert len(traces) == 2  # two task_ids

    def test_numeric_outcomes(self):
        events = [
            {"task_id": "t1", "node_id": "n1", "outcome": 1.0, "timestamp": 0},
            {"task_id": "t1", "node_id": "n1", "outcome": 0.0, "timestamp": 1},
        ]
        traces = from_generic_events(events)
        assert len(traces) == 1
        assert len(traces[0].outcomes) == 2

    def test_with_correction_field(self):
        events = [
            {
                "task_id": "t1", "node_id": "gen",
                "outcome": 0, "corrected": 1,
                "reviewed": True, "timestamp": 0,
            },
        ]
        traces = from_generic_events(
            events,
            corrected_field="corrected",
            reviewed_field="reviewed",
        )
        assert traces[0].outcomes[0].raw_outcome == 0.0
        assert traces[0].outcomes[0].corrected_outcome == 1.0
        assert traces[0].outcomes[0].was_reviewed is True

    def test_to_workflow_traces(self):
        events = [
            {"task_id": "t1", "node_id": "gen", "outcome": 1, "timestamp": 0},
        ]
        norm_traces = from_generic_events(events)
        wf_traces = to_workflow_traces(norm_traces)
        assert len(wf_traces) == 1
        assert wf_traces[0].node_outcomes["gen"] == 1.0


class TestLangGraphConnector:
    """Tests for normalize_langgraph using mock objects."""

    def _make_mock_graph(self, nodes, edges, conditional_edges=None, branches=None):
        """Build a mock object mimicking a LangGraph CompiledGraph."""

        class MockInner:
            pass

        class MockOuter:
            pass

        inner = MockInner()
        inner.nodes = nodes
        inner.edges = edges
        if conditional_edges is not None:
            inner.conditional_edges = conditional_edges
        if branches is not None:
            inner.branches = branches

        outer = MockOuter()
        outer.graph = inner
        return outer

    def test_simple_two_node_graph(self):
        def generate():
            """Generates draft text."""

        def review():
            """Reviews the draft."""

        graph = self._make_mock_graph(
            nodes={"generator": generate, "reviewer": review},
            edges=[("__start__", "generator"), ("generator", "reviewer"), ("reviewer", "__end__")],
        )
        normalized = normalize_langgraph(graph)
        assert len(normalized.nodes) == 2
        node_ids = [n.id for n in normalized.nodes]
        assert "generator" in node_ids
        assert "reviewer" in node_ids
        # __start__ and __end__ are filtered
        assert "__start__" not in node_ids
        assert "__end__" not in node_ids
        # Edge from generator -> reviewer
        assert len(normalized.edges) == 1
        assert normalized.edges[0].source_id == "generator"
        assert normalized.edges[0].target_id == "reviewer"

    def test_role_inference_from_node_names(self):
        def my_writer():
            """Writes content."""

        def my_checker():
            """Checks quality."""

        graph = self._make_mock_graph(
            nodes={"my_writer": my_writer, "my_checker": my_checker},
            edges=[("my_writer", "my_checker")],
        )
        normalized = normalize_langgraph(graph)
        roles = {n.id: n.role for n in normalized.nodes}
        assert roles["my_writer"] == NodeRole.GENERATOR
        assert roles["my_checker"] == NodeRole.REVIEWER

    def test_conditional_edges_dict_format(self):
        """Conditional edges as {source: {condition: target}} dict."""

        def router():
            """Routes requests."""

        def handler_a():
            """Handles type A."""

        def handler_b():
            """Handles type B."""

        graph = self._make_mock_graph(
            nodes={"router": router, "handler_a": handler_a, "handler_b": handler_b},
            edges=[("__start__", "router")],
            conditional_edges={"router": {"type_a": "handler_a", "type_b": "handler_b"}},
        )
        normalized = normalize_langgraph(graph)
        edge_pairs = [(e.source_id, e.target_id) for e in normalized.edges]
        assert ("router", "handler_a") in edge_pairs
        assert ("router", "handler_b") in edge_pairs

    def test_branches_attribute(self):
        """Conditional edges found under 'branches' attribute with Branch objects."""

        def router():
            """Routes."""

        def worker():
            """Works."""

        class MockBranch:
            def __init__(self, ends=None, then=None):
                self.ends = ends
                self.then = then

        graph = self._make_mock_graph(
            nodes={"router": router, "worker": worker},
            edges=[("__start__", "router")],
            branches={"router": [MockBranch(ends={"done": "worker"})]},
        )
        normalized = normalize_langgraph(graph)
        edge_pairs = [(e.source_id, e.target_id) for e in normalized.edges]
        assert ("router", "worker") in edge_pairs

    def test_deduplicates_edges(self):
        def a():
            pass

        def b():
            pass

        graph = self._make_mock_graph(
            nodes={"a": a, "b": b},
            edges=[("a", "b"), ("a", "b")],  # duplicate
        )
        normalized = normalize_langgraph(graph)
        assert len(normalized.edges) == 1

    def test_framework_source(self):
        graph = self._make_mock_graph(nodes={}, edges=[])
        normalized = normalize_langgraph(graph)
        assert normalized.framework_source == "langgraph"

    def test_builder_path(self):
        """Compiled graphs with .builder (real LangGraph) instead of .graph."""

        def gen():
            """Generates."""

        def rev():
            """Reviews."""

        class MockCompiled:
            pass

        class MockBuilder:
            pass

        builder = MockBuilder()
        builder.nodes = {"gen": gen, "rev": rev}
        builder.edges = [("__start__", "gen"), ("gen", "rev"), ("rev", "__end__")]

        compiled = MockCompiled()
        compiled.builder = builder

        normalized = normalize_langgraph(compiled)
        assert len(normalized.nodes) == 2
        assert any(e.source_id == "gen" and e.target_id == "rev" for e in normalized.edges)

    def test_branchspec_conditional_edges(self):
        """Real LangGraph branches: {source: {name: BranchSpec(ends={...})}}."""

        def router():
            """Routes."""

        def handler_a():
            """Handles A."""

        def handler_b():
            """Handles B."""

        class MockBranchSpec:
            def __init__(self, ends=None):
                self.ends = ends

        graph = self._make_mock_graph(
            nodes={"router": router, "handler_a": handler_a, "handler_b": handler_b},
            edges=[("__start__", "router")],
            branches={"router": {"condition": MockBranchSpec(ends={"a": "handler_a", "b": "handler_b"})}},
        )
        normalized = normalize_langgraph(graph)
        edge_pairs = [(e.source_id, e.target_id) for e in normalized.edges]
        assert ("router", "handler_a") in edge_pairs
        assert ("router", "handler_b") in edge_pairs

    def test_real_langgraph_if_available(self):
        """Integration test with real langgraph (skipped if not installed)."""
        pytest.importorskip("langgraph")
        from langgraph.graph import StateGraph, END
        from typing import TypedDict

        class St(TypedDict):
            x: str

        def a(s):
            """Does A."""
            return s

        def b(s):
            """Does B."""
            return s

        g = StateGraph(St)
        g.add_node("writer", a)
        g.add_node("checker", b)
        g.add_edge("writer", "checker")
        g.add_edge("checker", END)
        g.set_entry_point("writer")
        compiled = g.compile()

        normalized = normalize_langgraph(compiled)
        assert len(normalized.nodes) == 2
        ids = [n.id for n in normalized.nodes]
        assert "writer" in ids
        assert "checker" in ids
        writer_node = next(n for n in normalized.nodes if n.id == "writer")
        assert "Does A" in writer_node.description


class TestLangSmithTraceParser:
    """Tests for from_langsmith_traces."""

    def test_simple_run(self):
        runs = [
            {
                "id": "run-1",
                "name": "generator",
                "run_type": "chain",
                "start_time": 100.0,
                "end_time": 200.0,
                "status": "success",
            }
        ]
        traces = from_langsmith_traces(runs)
        assert len(traces) == 1
        assert traces[0].trace_id == "run-1"
        assert len(traces[0].outcomes) == 1
        assert traces[0].outcomes[0].raw_outcome == 1.0

    def test_iso8601_timestamps_parsed(self):
        """M2 fix: ISO-8601 timestamps should be parsed, not fall back to 0.0."""
        runs = [
            {
                "id": "run-2",
                "name": "node_a",
                "run_type": "llm",
                "start_time": "2025-01-15T10:00:00+00:00",
                "end_time": "2025-01-15T10:00:05+00:00",
                "status": "success",
            }
        ]
        traces = from_langsmith_traces(runs)
        assert len(traces) == 1
        events = traces[0].events
        # The start_time should not be 0.0
        assert events[0].timestamp > 0.0
        # end_time should be ~5 seconds after start_time
        assert events[1].timestamp - events[0].timestamp == pytest.approx(5.0, abs=0.1)

    def test_error_run(self):
        runs = [
            {
                "id": "run-err",
                "name": "failing_node",
                "run_type": "chain",
                "start_time": 0.0,
                "end_time": 1.0,
                "status": "error",
                "error": "something broke",
            }
        ]
        traces = from_langsmith_traces(runs)
        assert traces[0].outcomes[0].raw_outcome == 0.0

    def test_child_runs(self):
        runs = [
            {
                "id": "parent",
                "name": "pipeline",
                "run_type": "chain",
                "start_time": 0.0,
                "end_time": 10.0,
                "status": "success",
                "child_runs": [
                    {
                        "name": "step_1",
                        "run_type": "llm",
                        "start_time": 1.0,
                        "end_time": 5.0,
                        "status": "success",
                    },
                    {
                        "name": "step_2",
                        "run_type": "tool",
                        "start_time": 5.0,
                        "end_time": 9.0,
                        "status": "success",
                    },
                ],
            }
        ]
        traces = from_langsmith_traces(runs)
        assert len(traces) == 1
        # parent + 2 children = 3 outcomes
        assert len(traces[0].outcomes) == 3

    def test_framework_source(self):
        runs = [{"id": "r1", "name": "n", "run_type": "chain", "status": "success"}]
        traces = from_langsmith_traces(runs)
        assert traces[0].framework_source == "langsmith"


class TestADKSessionLogParser:
    """Tests for from_adk_session_logs."""

    def test_simple_session(self):
        sessions = [
            {
                "id": "sess-1",
                "events": [
                    {"agent": "router", "type": "tool_call", "timestamp": 1.0},
                    {"agent": "worker", "type": "response", "timestamp": 2.0},
                ],
            }
        ]
        traces = from_adk_session_logs(sessions)
        assert len(traces) == 1
        assert traces[0].trace_id == "sess-1"
        # Both are task-processing events, so both get outcomes
        assert len(traces[0].outcomes) == 2

    def test_handoff_events_excluded_from_outcomes(self):
        """M4 fix: handoff/transfer events should not create outcomes."""
        sessions = [
            {
                "id": "sess-2",
                "events": [
                    {"agent": "router", "type": "transfer", "timestamp": 1.0},
                    {"agent": "worker", "type": "response", "timestamp": 2.0},
                    {"agent": "router", "type": "handoff", "timestamp": 3.0},
                ],
            }
        ]
        traces = from_adk_session_logs(sessions)
        # Only 1 outcome (the "response" event); transfer and handoff are excluded
        assert len(traces[0].outcomes) == 1
        assert traces[0].outcomes[0].node_id == "worker"
        # But all 3 events should still be recorded
        assert len(traces[0].events) == 3

    def test_error_event(self):
        sessions = [
            {
                "id": "sess-3",
                "events": [
                    {"agent": "failing", "type": "error", "timestamp": 0.0},
                ],
            }
        ]
        traces = from_adk_session_logs(sessions)
        assert traces[0].outcomes[0].raw_outcome == 0.0
        assert traces[0].events[0].event_type == EventType.ERROR

    def test_iso_timestamps_parsed(self):
        """Timestamps as ISO strings should be parsed correctly."""
        sessions = [
            {
                "id": "sess-ts",
                "events": [
                    {"agent": "a", "type": "response", "timestamp": "2025-06-01T12:00:00+00:00"},
                ],
            }
        ]
        traces = from_adk_session_logs(sessions)
        assert traces[0].events[0].timestamp > 0.0

    def test_framework_source(self):
        sessions = [{"id": "s1", "events": []}]
        traces = from_adk_session_logs(sessions)
        assert traces[0].framework_source == "adk"


class TestDuplicateNodeIDs:
    """C1 fix: duplicate node IDs in ADK connector should use hierarchical paths."""

    def test_same_name_different_parents(self):
        config = {
            "name": "root",
            "sub_agents": [
                {
                    "name": "worker",
                    "description": "First worker group",
                    "sub_agents": [
                        {"name": "helper", "description": "Helps worker"},
                    ],
                },
                {
                    "name": "reviewer",
                    "description": "Review group",
                    "sub_agents": [
                        {"name": "helper", "description": "Helps reviewer"},
                    ],
                },
            ],
        }
        normalized = normalize_adk_config(config)
        ids = [n.id for n in normalized.nodes]
        # Both "helper" agents should have unique IDs
        assert "root/worker/helper" in ids
        assert "root/reviewer/helper" in ids
        # Should be 5 unique nodes total
        assert len(ids) == len(set(ids))
        assert len(ids) == 5


class TestRootAgentRole:
    """M7 fix: root agent without sub_agents should not be forced to ROUTER."""

    def test_single_agent_not_router(self):
        config = {"name": "my_agent", "description": "A simple agent"}
        normalized = normalize_adk_config(config)
        assert len(normalized.nodes) == 1
        # Single agent with no sub_agents should NOT be ROUTER
        assert normalized.nodes[0].role != NodeRole.ROUTER

    def test_root_with_sub_agents_defaults_to_router(self):
        """When infer_role returns UNKNOWN and root has sub_agents, default to ROUTER."""
        config = {
            "name": "orchestrator_v2",
            "sub_agents": [{"name": "child"}],
        }
        normalized = normalize_adk_config(config)
        root = [n for n in normalized.nodes if n.id == "orchestrator_v2"][0]
        # "orchestrator_v2" doesn't match any role pattern, but since it
        # has sub_agents it should default to ROUTER.
        assert root.role == NodeRole.ROUTER


class TestOutcomeAggregation:
    """M1 fix: duplicate (task_id, node_id) outcomes should be aggregated."""

    def test_warns_on_duplicate_outcomes(self):
        traces = [
            NormalizedTrace(
                trace_id="t1",
                outcomes=[
                    NormalizedOutcome(task_id="t1", node_id="n1", raw_outcome=1.0, corrected_outcome=1.0),
                    NormalizedOutcome(task_id="t1", node_id="n1", raw_outcome=0.0, corrected_outcome=0.0),
                ],
            )
        ]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            wf_traces = traces_from_normalized(traces)
            # Should produce a warning about aggregation
            assert len(w) == 1
            assert "Multiple outcomes" in str(w[0].message)
        # Mean of 1.0 and 0.0
        assert wf_traces[0].node_outcomes["n1"] == pytest.approx(0.5)
        assert wf_traces[0].node_corrected["n1"] == pytest.approx(0.5)


class TestAutoDetection:
    """M3 fix: auto-detection should require 'sub_agents' for ADK dicts."""

    def test_dict_with_only_name_raises(self):
        """A dict with just 'name' should NOT be auto-detected as ADK."""
        from minimal_oversight._api import _auto_convert
        with pytest.raises(TypeError):
            _auto_convert({"name": "something", "foo": "bar"})
