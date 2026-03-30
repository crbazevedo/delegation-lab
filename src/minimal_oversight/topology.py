"""Topology: graph-aware analysis of delegation DAGs.

Answers: "Where are the structural risks in this pipeline?"
Practitioners need this more than they think.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import networkx as nx
import numpy as np

from minimal_oversight.models import Node, PipelineGraph


class Motif(Enum):
    """Canonical delegation motifs (Table 2 in the paper)."""

    CHAIN = "chain"
    FAN_OUT = "fan_out"
    FAN_IN = "fan_in"
    DIAMOND = "diamond"
    MERGE = "merge"
    SINGLE = "single"


@dataclass
class MotifInstance:
    """A detected motif in the pipeline."""

    motif: Motif
    nodes: list[str]
    risk_description: str


@dataclass
class NodeRisk:
    """Risk profile for a single node."""

    name: str
    delegation_centrality: float
    masking_index: float | None
    sota_score: float | None
    fan_out_degree: int
    fan_in_degree: int
    is_bottleneck: bool
    motifs: list[Motif]


def delegation_centrality(
    pipeline: PipelineGraph,
    name: str,
) -> float:
    """Delegation centrality DC(v): fan-out degree weighted by downstream depth.

    Nodes with high DC have the most leverage — a single correction propagates
    to many downstream nodes.
    """
    g = pipeline.graph

    # Count all downstream nodes reachable from this node
    descendants = nx.descendants(g, name)
    out_degree = pipeline.fan_out(name)

    if not descendants:
        return float(out_degree)

    # Weight by distance: closer descendants matter more
    lengths = nx.single_source_shortest_path_length(g, name)
    weighted = sum(1.0 / d for n, d in lengths.items() if n != name and d > 0)

    return float(out_degree) * (1.0 + weighted)


def detect_motifs(pipeline: PipelineGraph) -> list[MotifInstance]:
    """Detect canonical delegation motifs in the pipeline.

    Returns a list of motif instances with risk descriptions.
    """
    motifs: list[MotifInstance] = []
    g = pipeline.graph

    if len(g.nodes) == 1:
        name = list(g.nodes)[0]
        motifs.append(MotifInstance(
            motif=Motif.SINGLE,
            nodes=[name],
            risk_description="Single delegation. Baseline masking applies.",
        ))
        return motifs

    # Detect chains (nodes with in-degree=1, out-degree=1)
    chain_nodes = [
        n for n in g.nodes
        if g.in_degree(n) == 1 and g.out_degree(n) == 1
    ]
    if chain_nodes:
        # Group contiguous chains
        visited: set[str] = set()
        for node in pipeline.topological_order():
            if node in visited or node not in chain_nodes:
                continue
            chain = [node]
            visited.add(node)
            # Extend forward
            current = node
            while True:
                succs = list(g.successors(current))
                if len(succs) == 1 and succs[0] in chain_nodes and succs[0] not in visited:
                    chain.append(succs[0])
                    visited.add(succs[0])
                    current = succs[0]
                else:
                    break
            if len(chain) >= 2:
                motifs.append(MotifInstance(
                    motif=Motif.CHAIN,
                    nodes=chain,
                    risk_description=(
                        f"Chain of depth {len(chain)}. "
                        "Masking and quality loss accumulate with depth. "
                        "Improve upstream quality first."
                    ),
                ))

    # Detect fan-out (nodes with out-degree > 1)
    for name in g.nodes:
        out_deg = g.out_degree(name)
        if out_deg > 1:
            children = list(g.successors(name))
            motifs.append(MotifInstance(
                motif=Motif.FAN_OUT,
                nodes=[name] + children,
                risk_description=(
                    f"Fan-out at {name} (degree {out_deg}). "
                    "One failure contaminates multiple branches. "
                    "Prioritize this node for review."
                ),
            ))

    # Detect fan-in / merge (nodes with in-degree > 1)
    for name in g.nodes:
        in_deg = g.in_degree(name)
        if in_deg > 1:
            parents = list(g.predecessors(name))
            motifs.append(MotifInstance(
                motif=Motif.MERGE,
                nodes=parents + [name],
                risk_description=(
                    f"Merge at {name} (fan-in {in_deg}). "
                    "Throughput and autonomy limited by bottleneck path. "
                    "Aggregation type determines masking severity."
                ),
            ))

    # Detect diamond patterns (two paths from A to D through different intermediates)
    for name in g.nodes:
        if g.in_degree(name) < 2:
            continue
        parents = list(g.predecessors(name))
        for i, p1 in enumerate(parents):
            for p2 in parents[i + 1 :]:
                # Check if p1 and p2 share a common ancestor
                ancestors_p1 = nx.ancestors(g, p1)
                ancestors_p2 = nx.ancestors(g, p2)
                shared = ancestors_p1 & ancestors_p2
                # Also check if one is ancestor of the other
                if p1 in ancestors_p2 or p2 in ancestors_p1:
                    shared.add(p1 if p1 in ancestors_p2 else p2)
                if shared:
                    source = max(shared, key=lambda n: nx.shortest_path_length(g, n, name))
                    motifs.append(MotifInstance(
                        motif=Motif.DIAMOND,
                        nodes=[source, p1, p2, name],
                        risk_description=(
                            f"Diamond: {source} → {{{p1}, {p2}}} → {name}. "
                            "Correlated upstream errors create conditional fragility. "
                            "Correct the shared source rather than hardening the merge."
                        ),
                    ))

    return motifs


def conditional_fragility(
    pipeline: PipelineGraph,
    merge_node: str,
    parent_sigma_corrs: dict[str, float],
    shared_source_catch_rate: float = 0.0,
) -> float:
    """Estimate conditional fragility ratio at a merge node.

    Fragility = P(D correct | A correct) / P(D correct | A error)

    Higher values indicate hidden vulnerability to shared upstream failure.
    """
    node = pipeline.get_node(merge_node)
    parents = pipeline.parents(merge_node)

    if not parents or len(parents) < 2:
        return 1.0

    # With upstream correction (A correct)
    quality_a_ok = np.prod([parent_sigma_corrs.get(p, 0.8) for p in parents])

    # Without upstream correction (A error): degrade all parents proportionally
    degraded = {
        p: parent_sigma_corrs.get(p, 0.8) * (1 - shared_source_catch_rate)
        for p in parents
    }
    quality_a_err = np.prod(list(degraded.values()))

    if quality_a_err <= 0:
        return float("inf")

    return float(quality_a_ok / quality_a_err)


def rank_nodes_by_risk(pipeline: PipelineGraph) -> list[NodeRisk]:
    """Rank all nodes by governance risk, highest first.

    Combines delegation centrality, masking, and structural position.
    """
    motif_instances = detect_motifs(pipeline)
    node_motifs: dict[str, list[Motif]] = {n: [] for n in pipeline.nodes}
    for mi in motif_instances:
        for n in mi.nodes:
            if n in node_motifs:
                node_motifs[n].append(mi.motif)

    risks: list[NodeRisk] = []
    for name, node in pipeline.nodes.items():
        dc = delegation_centrality(pipeline, name)
        m_star = node.masking_index

        # SOTA score if we have the data
        kappa = (1.0 - node.sigma_skill) if node.sigma_skill is not None else None
        sota = dc * m_star * kappa if m_star is not None and kappa is not None else None

        # Simple bottleneck heuristic: high fan-in or low capacity
        is_bottleneck = pipeline.fan_in(name) > 1

        risks.append(NodeRisk(
            name=name,
            delegation_centrality=dc,
            masking_index=m_star,
            sota_score=sota,
            fan_out_degree=pipeline.fan_out(name),
            fan_in_degree=pipeline.fan_in(name),
            is_bottleneck=is_bottleneck,
            motifs=list(set(node_motifs[name])),
        ))

    # Sort by SOTA score (desc), falling back to delegation centrality
    risks.sort(
        key=lambda r: (r.sota_score if r.sota_score is not None else 0.0, r.delegation_centrality),
        reverse=True,
    )
    return risks
