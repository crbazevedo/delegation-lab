"""Bridge: convert canonical schema to internal models.

This is the single translation point between the normalized schema
and the PipelineGraph / WorkflowTrace objects used by the analytics layer.
"""

from __future__ import annotations

import warnings
from collections import defaultdict

from minimal_oversight.models import AggregationType, Node, PipelineGraph, WorkflowTrace
from minimal_oversight.schema import (
    NormalizedOutcome,
    NormalizedPipeline,
    NormalizedTrace,
    NodeRole,
    defaults_for_role,
)


def _role_to_aggregation(role: NodeRole) -> AggregationType:
    """Return the default aggregation type.

    Aggregation is topology-dependent, not role-dependent, so we always
    default to PRODUCT.  Users can override per-node after import.
    """
    return AggregationType.PRODUCT


def pipeline_from_normalized(
    normalized: NormalizedPipeline,
    parameter_overrides: dict[str, dict[str, float]] | None = None,
) -> PipelineGraph:
    """Convert a NormalizedPipeline to a PipelineGraph for analysis.

    Parameters are bootstrapped from role defaults. Override with
    ``parameter_overrides`` keyed by node ID, or calibrate later with traces.

    Args:
        normalized: The canonical pipeline representation.
        parameter_overrides: Optional dict of {node_id: {param: value}} to
            override default parameters.

    Returns:
        A PipelineGraph ready for analyze_pipeline().
    """
    overrides = parameter_overrides or {}
    nodes: list[Node] = []

    for n_node in normalized.nodes:
        defaults = defaults_for_role(n_node.role)
        node_overrides = overrides.get(n_node.id, {})

        node = Node(
            name=n_node.id,
            sigma_skill=node_overrides.get("sigma_skill", defaults["sigma_skill"]),
            catch_rate=node_overrides.get("catch_rate", defaults["catch_rate"]),
            review_capacity=node_overrides.get("review_capacity", defaults["review_capacity"]),
            aggregation=_role_to_aggregation(n_node.role),
            metadata={
                "display_name": n_node.name,
                "role": n_node.role.value,
                "description": n_node.description,
                "model": n_node.model,
                "framework_type": n_node.framework_type,
                "framework_source": normalized.framework_source,
                **n_node.framework_metadata,
            },
        )
        nodes.append(node)

    pipeline = PipelineGraph(nodes)

    for edge in normalized.edges:
        pipeline.add_edge(edge.source_id, edge.target_id)

    return pipeline


def traces_from_normalized(
    normalized_traces: list[NormalizedTrace],
) -> list[WorkflowTrace]:
    """Convert normalized traces to WorkflowTrace objects for estimation.

    Maps NormalizedOutcome pairs to the node_outcomes / node_corrected dicts
    expected by the estimation module.
    """
    traces: list[WorkflowTrace] = []

    # Group outcomes by task_id across all traces
    task_outcomes: dict[str, list[NormalizedOutcome]] = {}
    for trace in normalized_traces:
        for outcome in trace.outcomes:
            task_outcomes.setdefault(outcome.task_id, []).append(outcome)

    for task_id, outcomes in task_outcomes.items():
        node_outcomes: dict[str, float] = {}
        node_corrected: dict[str, float] = {}
        was_reviewed: dict[str, bool] = {}
        timestamps: dict[str, float] = {}
        routing_path: list[str] = []

        # Collect all values per node to aggregate duplicates
        raw_values: dict[str, list[float]] = defaultdict(list)
        corr_values: dict[str, list[float]] = defaultdict(list)

        for o in outcomes:
            raw_values[o.node_id].append(o.raw_outcome)
            corr_values[o.node_id].append(o.corrected_outcome)
            # For reviewed flag, use OR: if any observation was reviewed, mark as reviewed
            was_reviewed[o.node_id] = was_reviewed.get(o.node_id, False) or o.was_reviewed
            if o.timestamp is not None:
                timestamps[o.node_id] = o.timestamp
            if o.node_id not in routing_path:
                routing_path.append(o.node_id)

        for node_id, raws in raw_values.items():
            if len(raws) > 1:
                warnings.warn(
                    f"Multiple outcomes for (task_id={task_id!r}, node_id={node_id!r}): "
                    f"aggregating {len(raws)} values by mean.",
                    stacklevel=2,
                )
            node_outcomes[node_id] = sum(raws) / len(raws)
            corrs = corr_values[node_id]
            node_corrected[node_id] = sum(corrs) / len(corrs)

        has_human = any(o.was_reviewed and o.reviewer_id == "human" for o in outcomes)

        traces.append(WorkflowTrace(
            task_id=task_id,
            node_outcomes=node_outcomes,
            node_corrected=node_corrected,
            routing_path=routing_path,
            timestamps=timestamps,
            was_reviewed=was_reviewed,
            human_intervention=has_human,
        ))

    return traces
