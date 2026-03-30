"""LangGraph connector: import pipelines from LangGraph StateGraph objects.

Translates a LangGraph ``StateGraph`` (or compiled ``CompiledGraph``) into
the canonical schema, which is then converted to a PipelineGraph for analysis.

Usage::

    from langgraph.graph import StateGraph
    from minimal_oversight.connectors.langgraph import from_langgraph

    # Your existing LangGraph workflow
    graph = StateGraph(MyState)
    graph.add_node("generator", generate_fn)
    graph.add_node("reviewer", review_fn)
    graph.add_edge("generator", "reviewer")
    compiled = graph.compile()

    # Import into minimal-oversight
    pipeline = from_langgraph(compiled)
    report = analyze_pipeline(pipeline, p_min=0.80)

Requires: ``pip install langgraph``
"""

from __future__ import annotations

from typing import Any

from minimal_oversight.connectors._bridge import pipeline_from_normalized
from minimal_oversight.connectors._roles import infer_role
from minimal_oversight.models import PipelineGraph
from minimal_oversight.schema import (
    NormalizedEdge,
    NormalizedNode,
    NormalizedPipeline,
)

# LangGraph special node names
_LG_START = "__start__"
_LG_END = "__end__"
_SKIP_NODES = {_LG_START, _LG_END}


def _extract_node_description(node_data: Any) -> str:
    """Best-effort extraction of a description from a LangGraph node.

    Handles multiple patterns:
    - Raw callables (function docstring)
    - StateNodeSpec wrappers (.runnable.func.__doc__)
    - Objects with .description attribute
    """
    # StateNodeSpec → runnable → func (real LangGraph compiled graphs)
    runnable = getattr(node_data, "runnable", None)
    if runnable is not None:
        func = getattr(runnable, "func", None)
        if func is not None and hasattr(func, "__doc__") and func.__doc__:
            return func.__doc__.strip().split("\n")[0]
        if hasattr(runnable, "__doc__") and runnable.__doc__:
            return runnable.__doc__.strip().split("\n")[0]

    # Direct docstring (raw callables, mock objects)
    if hasattr(node_data, "__doc__") and node_data.__doc__:
        return node_data.__doc__.strip().split("\n")[0]
    if hasattr(node_data, "description") and node_data.description:
        return str(node_data.description)
    if callable(node_data) and hasattr(node_data, "__name__"):
        return node_data.__name__
    return ""


def _extract_model_name(node_data: Any) -> str | None:
    """Best-effort extraction of the LLM model from a LangGraph node."""
    # Check for common LLM wrapper patterns
    if hasattr(node_data, "model_name"):
        return str(node_data.model_name)
    if hasattr(node_data, "model"):
        model = node_data.model
        if hasattr(model, "model_name"):
            return str(model.model_name)
        if isinstance(model, str):
            return model
    if hasattr(node_data, "llm"):
        llm = node_data.llm
        if hasattr(llm, "model_name"):
            return str(llm.model_name)
    return None


def normalize_langgraph(graph: Any) -> NormalizedPipeline:
    """Convert a LangGraph graph to the canonical NormalizedPipeline.

    Accepts either a ``StateGraph`` or a ``CompiledGraph``.

    Args:
        graph: A LangGraph StateGraph or CompiledGraph object.

    Returns:
        NormalizedPipeline with inferred roles and edges.
    """
    # Handle compiled, uncompiled, and builder patterns.
    # Real CompiledStateGraph has .builder (the StateGraph), not .graph.
    # Some versions/mocks use .graph. Try all patterns.
    if hasattr(graph, "builder"):
        inner = graph.builder
    elif hasattr(graph, "graph"):
        inner = graph.graph
    else:
        inner = graph

    # Extract nodes
    nodes_dict: dict[str, Any] = {}
    if hasattr(inner, "nodes"):
        nodes_raw = inner.nodes
        if isinstance(nodes_raw, dict):
            nodes_dict = nodes_raw
        elif hasattr(nodes_raw, "items"):
            nodes_dict = dict(nodes_raw.items())

    # Extract edges
    edges_raw: list[tuple[str, str]] = []
    if hasattr(inner, "edges"):
        for edge in inner.edges:
            if isinstance(edge, tuple) and len(edge) >= 2:
                edges_raw.append((str(edge[0]), str(edge[1])))

    # Also check conditional edges — try multiple attribute names since
    # LangGraph internals vary across versions.
    _conditional_attrs = [
        "conditional_edges",
        "_conditional_edges",
        "branches",
        "_branches",
    ]
    for attr_name in _conditional_attrs:
        cond_data = getattr(inner, attr_name, None)
        if cond_data is None:
            continue
        if isinstance(cond_data, dict):
            for src, branch_val in cond_data.items():
                if isinstance(branch_val, dict):
                    # {source: {condition_result: target_node}}
                    for _, tgt in branch_val.items():
                        if isinstance(tgt, str):
                            edges_raw.append((str(src), tgt))
                elif isinstance(branch_val, list):
                    # {source: [Branch(...)]} — LangGraph Branch objects
                    for branch in branch_val:
                        # Branch objects may have .ends (dict) or .then (str)
                        ends = getattr(branch, "ends", None)
                        if isinstance(ends, dict):
                            for _, tgt in ends.items():
                                if isinstance(tgt, str):
                                    edges_raw.append((str(src), tgt))
                        then = getattr(branch, "then", None)
                        if isinstance(then, str):
                            edges_raw.append((str(src), then))
            break  # found a valid attribute, stop searching

    # Build normalized nodes (skip __start__ and __end__)
    normalized_nodes: list[NormalizedNode] = []
    for node_id, node_data in nodes_dict.items():
        if node_id in _SKIP_NODES:
            continue

        description = _extract_node_description(node_data)
        model = _extract_model_name(node_data)
        role = infer_role(node_id, description)

        normalized_nodes.append(NormalizedNode(
            id=node_id,
            name=node_id,
            role=role,
            description=description,
            model=model,
            framework_type="langgraph_node",
            framework_metadata={"original_type": type(node_data).__name__},
        ))

    # Build normalized edges (skip edges involving __start__/__end__)
    node_ids = {n.id for n in normalized_nodes}
    normalized_edges: list[NormalizedEdge] = []
    seen_edges: set[tuple[str, str]] = set()

    for src, tgt in edges_raw:
        if src in _SKIP_NODES or tgt in _SKIP_NODES:
            # Remap __start__ edges: connect to first real node if needed
            continue
        if src not in node_ids or tgt not in node_ids:
            continue
        edge_key = (src, tgt)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)

        normalized_edges.append(NormalizedEdge(
            source_id=src,
            target_id=tgt,
        ))

    return NormalizedPipeline(
        nodes=normalized_nodes,
        edges=normalized_edges,
        framework_source="langgraph",
    )


def from_langgraph(
    graph: Any,
    parameter_overrides: dict[str, dict[str, float]] | None = None,
) -> PipelineGraph:
    """Import a LangGraph graph directly as a PipelineGraph.

    This is the convenience function most users will call.

    Args:
        graph: A LangGraph StateGraph or CompiledGraph.
        parameter_overrides: Optional per-node parameter overrides.

    Returns:
        A PipelineGraph ready for analyze_pipeline().
    """
    normalized = normalize_langgraph(graph)
    return pipeline_from_normalized(normalized, parameter_overrides)
