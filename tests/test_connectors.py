"""Tests for framework connectors (without requiring actual frameworks installed)."""

import pytest

from minimal_oversight import analyze_pipeline
from minimal_oversight.connectors.adk import from_adk_config, normalize_adk_config
from minimal_oversight.connectors.traces import from_generic_events, to_workflow_traces
from minimal_oversight.schema import NodeRole


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
        assert pipeline.children("support_agent") == ["billing_agent", "tech_support"]

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
        assert "lint_check" in pipeline.children("reviewer")

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
        assert roles["code_generator"] == NodeRole.GENERATOR
        assert roles["code_reviewer"] == NodeRole.REVIEWER
        assert roles["security_check"] == NodeRole.REVIEWER

    def test_parameter_overrides(self):
        config = {"name": "agent", "sub_agents": [{"name": "worker"}]}
        overrides = {"worker": {"sigma_skill": 0.90}}
        pipeline = from_adk_config(config, parameter_overrides=overrides)
        assert pipeline.get_node("worker").sigma_skill == 0.90

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
