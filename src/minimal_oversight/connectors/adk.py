"""Google ADK connector: import pipelines from ADK agent configurations.

Translates Google Agent Development Kit (ADK) agent hierarchies into
the canonical schema. ADK agents use a hierarchical model where a root
agent delegates to sub-agents via transfers/handoffs.

Usage::

    from minimal_oversight.connectors.adk import from_adk_config

    # From a dict (parsed YAML/JSON agent config)
    config = {
        "name": "support_agent",
        "model": "gemini-2.0-flash",
        "sub_agents": [
            {"name": "billing_agent", "model": "gemini-2.0-flash"},
            {"name": "tech_support", "model": "gemini-2.0-flash"},
        ]
    }
    pipeline = from_adk_config(config)
    report = analyze_pipeline(pipeline, p_min=0.80)

    # Or from an ADK Agent object
    from google.adk import Agent
    agent = Agent(name="root", sub_agents=[...])
    pipeline = from_adk_agent(agent)

Requires: ``pip install google-adk`` (for Agent object import; dict config works without it)
"""

from __future__ import annotations

from typing import Any

from minimal_oversight.connectors._bridge import pipeline_from_normalized
from minimal_oversight.connectors._roles import infer_role
from minimal_oversight.models import PipelineGraph
from minimal_oversight.schema import (
    NodeRole,
    NormalizedEdge,
    NormalizedNode,
    NormalizedPipeline,
)


def _walk_agent_config(
    config: dict[str, Any],
    nodes: list[NormalizedNode],
    edges: list[NormalizedEdge],
    parent_id: str | None = None,
) -> None:
    """Recursively walk an ADK agent config dict, building nodes and edges."""
    agent_name = config.get("name", "unnamed")
    # Use hierarchical path to avoid duplicate IDs when sub-agents share names
    agent_id = f"{parent_id}/{agent_name}" if parent_id is not None else agent_name
    description = config.get("description", config.get("instruction", ""))
    model = config.get("model", None)

    # Infer role
    sub_agents = config.get("sub_agents", [])
    role = infer_role(agent_name, description)
    if parent_id is None and role == NodeRole.UNKNOWN:
        # Only default to ROUTER if this agent actually delegates
        if sub_agents:
            role = NodeRole.ROUTER
        else:
            role = NodeRole.GENERATOR

    nodes.append(NormalizedNode(
        id=agent_id,
        name=agent_name,
        role=role,
        description=description[:200] if description else "",
        model=model,
        framework_type="adk_agent",
        framework_metadata={
            k: v for k, v in config.items()
            if k not in ("name", "description", "instruction", "model", "sub_agents", "tools")
        },
    ))

    # Edge from parent
    if parent_id is not None:
        edges.append(NormalizedEdge(
            source_id=parent_id,
            target_id=agent_id,
            is_handoff=True,
        ))

    # Recurse into sub-agents
    for sub in sub_agents:
        if isinstance(sub, dict):
            _walk_agent_config(sub, nodes, edges, parent_id=agent_id)


def _walk_adk_agent(
    agent: Any,
    nodes: list[NormalizedNode],
    edges: list[NormalizedEdge],
    parent_id: str | None = None,
) -> None:
    """Recursively walk an ADK Agent object."""
    agent_name = getattr(agent, "name", "unnamed")
    # Use hierarchical path to avoid duplicate IDs when sub-agents share names
    agent_id = f"{parent_id}/{agent_name}" if parent_id is not None else agent_name
    description = getattr(agent, "description", "") or getattr(agent, "instruction", "") or ""
    model = getattr(agent, "model", None)
    if model and not isinstance(model, str):
        model = str(model)

    sub_agents = getattr(agent, "sub_agents", []) or []
    role = infer_role(agent_name, description)
    if parent_id is None and role == NodeRole.UNKNOWN:
        # Only default to ROUTER if this agent actually delegates
        if sub_agents:
            role = NodeRole.ROUTER
        else:
            role = NodeRole.GENERATOR

    nodes.append(NormalizedNode(
        id=agent_id,
        name=agent_name,
        role=role,
        description=description[:200] if description else "",
        model=model,
        framework_type="adk_agent",
    ))

    if parent_id is not None:
        edges.append(NormalizedEdge(
            source_id=parent_id,
            target_id=agent_id,
            is_handoff=True,
        ))

    # Recurse
    for sub in sub_agents:
        _walk_adk_agent(sub, nodes, edges, parent_id=agent_id)


def normalize_adk_config(config: dict[str, Any]) -> NormalizedPipeline:
    """Convert an ADK agent config dict to a NormalizedPipeline.

    Args:
        config: Agent configuration as a dict (from parsed YAML/JSON).
    """
    nodes: list[NormalizedNode] = []
    edges: list[NormalizedEdge] = []
    _walk_agent_config(config, nodes, edges)

    return NormalizedPipeline(
        nodes=nodes,
        edges=edges,
        framework_source="adk",
    )


def normalize_adk_agent(agent: Any) -> NormalizedPipeline:
    """Convert an ADK Agent object to a NormalizedPipeline.

    Args:
        agent: A google.adk.Agent (or compatible) object.
    """
    nodes: list[NormalizedNode] = []
    edges: list[NormalizedEdge] = []
    _walk_adk_agent(agent, nodes, edges)

    return NormalizedPipeline(
        nodes=nodes,
        edges=edges,
        framework_source="adk",
    )


def from_adk_config(
    config: dict[str, Any],
    parameter_overrides: dict[str, dict[str, float]] | None = None,
) -> PipelineGraph:
    """Import an ADK agent config as a PipelineGraph.

    Args:
        config: Agent config dict (parsed YAML/JSON).
        parameter_overrides: Optional per-node parameter overrides.
    """
    normalized = normalize_adk_config(config)
    return pipeline_from_normalized(normalized, parameter_overrides)


def from_adk_agent(
    agent: Any,
    parameter_overrides: dict[str, dict[str, float]] | None = None,
) -> PipelineGraph:
    """Import an ADK Agent object as a PipelineGraph.

    Args:
        agent: A google.adk.Agent object.
        parameter_overrides: Optional per-node parameter overrides.
    """
    normalized = normalize_adk_agent(agent)
    return pipeline_from_normalized(normalized, parameter_overrides)
