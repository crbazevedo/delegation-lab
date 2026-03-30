"""Core data models for governed delegation.

Typed objects for the paper's primitives: nodes, pipelines, governance policies,
and workflow traces. Boring and explicit by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import networkx as nx
import numpy as np


class AggregationType(Enum):
    """How a merge node combines inputs from its parents."""

    PRODUCT = "product"  # each input contributes independently; errors compound
    WEAKEST_LINK = "min"  # limited by worst parent
    WEIGHTED_MEAN = "mean"  # weighted average across inputs


@dataclass
class Node:
    """A single delegation node (agent + optional corrector).

    Attributes:
        name: Human-readable identifier.
        sigma_skill: True competence (if known); often estimated.
        sigma_raw: Observed raw competence (pre-correction success rate).
        sigma_corr: Observed corrected quality (post-correction success rate).
        catch_rate: Corrector's error-catch probability *c*.
        review_capacity: Fraction of outputs the corrector reviews (*K/N*).
        drift_rate: Estimated skill degradation rate *mu_eff*.
        noise_var: Estimated noise variance *nu_eff^2*.
        aggregation: How this node merges inputs (only relevant for merge nodes).
        metadata: Arbitrary extra data for user extensions.
    """

    name: str
    sigma_skill: float | None = None
    sigma_raw: float | None = None
    sigma_corr: float | None = None
    catch_rate: float | None = None
    review_capacity: float | None = None
    drift_rate: float | None = None
    noise_var: float | None = None
    aggregation: AggregationType = AggregationType.PRODUCT
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def masking_index(self) -> float | None:
        """M* = sigma_corr / sigma_raw. None if either signal is missing."""
        if self.sigma_corr is not None and self.sigma_raw is not None and self.sigma_raw > 0:
            return self.sigma_corr / self.sigma_raw
        return None


@dataclass
class GovernancePolicy:
    """Parameters governing a delegation.

    Attributes:
        p_min: Minimum acceptable quality target.
        review_budget: Average review-cost budget *B* across the pipeline.
        alpha_max: Maximum authority any single node can receive.
        routing_rule: Description of the routing policy (free-form for v1).
        scope_rule: Description of scope policy (free-form for v1).
        intervention_thresholds: Per-node or global thresholds for alerts.
    """

    p_min: float = 0.80
    review_budget: float | None = None
    alpha_max: float = 1.0
    routing_rule: str | None = None
    scope_rule: str | None = None
    intervention_thresholds: dict[str, float] = field(default_factory=dict)


@dataclass
class WorkflowTrace:
    """A single observed item passing through the pipeline.

    Attributes:
        task_id: Unique identifier for this item.
        node_outcomes: Dict mapping node name -> pre-correction outcome (0/1 or float).
        node_corrected: Dict mapping node name -> post-correction outcome.
        routing_path: Ordered list of node names this item visited.
        timestamps: Dict mapping node name -> processing timestamp.
        was_reviewed: Dict mapping node name -> whether corrector reviewed this item.
        human_intervention: Whether a human intervened on this item.
    """

    task_id: str
    node_outcomes: dict[str, float] = field(default_factory=dict)
    node_corrected: dict[str, float] = field(default_factory=dict)
    routing_path: list[str] = field(default_factory=list)
    timestamps: dict[str, float] = field(default_factory=dict)
    was_reviewed: dict[str, bool] = field(default_factory=dict)
    human_intervention: bool = False


class PipelineGraph:
    """A delegation DAG: nodes connected by directed edges.

    Wraps a ``networkx.DiGraph`` with typed ``Node`` objects and provides
    convenience accessors for the paper's topological analysis.
    """

    def __init__(self, nodes: list[Node] | None = None) -> None:
        self._graph = nx.DiGraph()
        self._nodes: dict[str, Node] = {}
        if nodes:
            for node in nodes:
                self.add_node(node)

    def add_node(self, node: Node) -> None:
        self._nodes[node.name] = node
        self._graph.add_node(node.name)

    def add_edge(self, source: str, target: str) -> None:
        if source not in self._nodes:
            raise ValueError(f"Unknown source node: {source!r}")
        if target not in self._nodes:
            raise ValueError(f"Unknown target node: {target!r}")
        self._graph.add_edge(source, target)

    def get_node(self, name: str) -> Node:
        return self._nodes[name]

    @property
    def nodes(self) -> dict[str, Node]:
        return dict(self._nodes)

    @property
    def graph(self) -> nx.DiGraph:
        """The underlying networkx DiGraph, for direct graph algorithms."""
        return self._graph

    @property
    def depth(self) -> int:
        """Longest path length in the DAG."""
        if not self._graph.nodes:
            return 0
        return nx.dag_longest_path_length(self._graph)

    def sources(self) -> list[str]:
        """Nodes with no parents (entry points)."""
        return [n for n in self._graph.nodes if self._graph.in_degree(n) == 0]

    def sinks(self) -> list[str]:
        """Nodes with no children (output points)."""
        return [n for n in self._graph.nodes if self._graph.out_degree(n) == 0]

    def parents(self, name: str) -> list[str]:
        return list(self._graph.predecessors(name))

    def children(self, name: str) -> list[str]:
        return list(self._graph.successors(name))

    def fan_out(self, name: str) -> int:
        return self._graph.out_degree(name)

    def fan_in(self, name: str) -> int:
        return self._graph.in_degree(name)

    def topological_order(self) -> list[str]:
        return list(nx.topological_sort(self._graph))

    def __repr__(self) -> str:
        return (
            f"PipelineGraph(nodes={len(self._nodes)}, "
            f"edges={self._graph.number_of_edges()}, "
            f"depth={self.depth})"
        )
