"""Capacity: operational feasibility and autonomy-limit tools.

Answers: "Can this pipeline hit the quality target at all?"
This is where the package becomes a decision tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from minimal_oversight import _formulae as F
from minimal_oversight.models import Node, PipelineGraph


@dataclass
class FeasibilityReport:
    """Result of a feasibility check.

    Attributes:
        feasible: Whether p_min ≤ C_op.
        c_op: Operational quality ceiling.
        p_min: Requested quality target.
        b_eff: Effective autonomy buffer (None if process entropy unknown).
        h_crit: Critical process entropy (None if lambda unknown).
        h_max: Maximum supportable process entropy (None if lambda unknown).
        bottleneck_node: The node limiting pipeline capacity (if identified).
        explanation: Human-readable verdict.
    """

    feasible: bool
    c_op: float
    p_min: float
    b_eff: float | None = None
    h_crit: float | None = None
    h_max: float | None = None
    bottleneck_node: str | None = None
    explanation: str = ""


def compute_node_capacity(
    node: Node,
    eta: float = 10.0,
    delta: float = 2.0,
) -> float:
    """Operational capacity of a single node.

    Uses recursive formula: C = σ*_corr at the node's fixed point.
    """
    sigma_skill = node.sigma_skill if node.sigma_skill is not None else 0.55
    catch_rate = node.catch_rate if node.catch_rate is not None else 0.65
    sigma_raw_star = F.sigma_raw_fixed_point(sigma_skill, eta, delta)
    return F.sigma_corr_fixed_point(sigma_raw_star, catch_rate)


def compute_pipeline_capacity(
    pipeline: PipelineGraph,
    eta: float = 10.0,
    delta: float = 2.0,
) -> dict[str, float]:
    """Compute operational capacity at each node in topological order.

    Each node's effective skill depends on its parents' corrected quality.

    Returns:
        Dict mapping node name -> C_op at that node.
    """
    capacities: dict[str, float] = {}
    node_sigma_corr: dict[str, float] = {}

    for name in pipeline.topological_order():
        node = pipeline.get_node(name)
        sigma_skill = node.sigma_skill if node.sigma_skill is not None else 0.55
        catch_rate = node.catch_rate if node.catch_rate is not None else 0.65

        # Effective skill incorporates parent corrected qualities
        parents = pipeline.parents(name)
        if parents:
            parent_corrs = [node_sigma_corr.get(p, 1.0) for p in parents]
            agg_type = node.aggregation.value
            sigma_skill_eff = F.effective_skill(sigma_skill, parent_corrs, agg_type)
        else:
            sigma_skill_eff = sigma_skill

        sigma_raw_star = F.sigma_raw_fixed_point(sigma_skill_eff, eta, delta)
        sigma_corr_star = F.sigma_corr_fixed_point(sigma_raw_star, catch_rate)

        node_sigma_corr[name] = sigma_corr_star
        capacities[name] = sigma_corr_star

    return capacities


def compute_c_op(pipeline: PipelineGraph, **kwargs: Any) -> float:
    """Pipeline operational ceiling: the minimum capacity across sink nodes."""
    caps = compute_pipeline_capacity(pipeline, **kwargs)
    sinks = pipeline.sinks()
    if not sinks:
        return 0.0
    return min(caps[s] for s in sinks)


def compute_buffer(
    c_op: float,
    p_min: float,
    governance_gap: float = 0.02,
    process_entropy: float = 0.0,
) -> float:
    """Effective autonomy buffer: B_eff = C_op − p_min − λH(W).

    Args:
        c_op: Operational quality ceiling.
        p_min: Quality target.
        governance_gap: λ (governance gap coefficient), typically ~0.02/bit.
        process_entropy: H(W) in bits.
    """
    return F.effective_autonomy_buffer(c_op, p_min, governance_gap, process_entropy)


def check_feasibility(
    pipeline: PipelineGraph,
    p_min: float = 0.80,
    governance_gap: float = 0.02,
    process_entropy: float = 0.0,
    eta: float = 10.0,
    delta: float = 2.0,
) -> FeasibilityReport:
    """Full feasibility check with human-readable explanation.

    This is the core decision function: "Can this pipeline work?"
    """
    capacities = compute_pipeline_capacity(pipeline, eta=eta, delta=delta)
    sinks = pipeline.sinks()

    if not sinks:
        return FeasibilityReport(
            feasible=False,
            c_op=0.0,
            p_min=p_min,
            explanation="Pipeline has no output nodes.",
        )

    # Pipeline C_op is the bottleneck
    c_op = min(capacities[s] for s in sinks)
    bottleneck = min(capacities, key=capacities.get)  # type: ignore[arg-type]

    b_eff = compute_buffer(c_op, p_min, governance_gap, process_entropy)
    h_crit = F.critical_entropy(c_op, p_min, governance_gap)

    feasible = c_op >= p_min
    buffer_ok = b_eff > 0

    # Build explanation
    lines = []
    if not feasible:
        lines.append(
            f"INFEASIBLE: Quality target p_min={p_min:.3f} exceeds pipeline "
            f"capacity C_op={c_op:.3f}."
        )
        lines.append(
            f"No governance policy can rescue this design. "
            f"Bottleneck: {bottleneck} (capacity={capacities[bottleneck]:.3f})."
        )
        lines.append(
            "Actions: improve agents, add better correctors, or change topology."
        )
    elif not buffer_ok:
        lines.append(
            f"FEASIBLE but AT RISK: C_op={c_op:.3f} ≥ p_min={p_min:.3f}, "
            f"but effective buffer B_eff={b_eff:.4f} ≤ 0 after accounting for "
            f"process entropy H(W)={process_entropy:.2f} bits."
        )
        lines.append(
            "The pipeline is near the autonomy cliff. Simplify routing or "
            "increase review capacity."
        )
    else:
        lines.append(
            f"FEASIBLE: C_op={c_op:.3f} ≥ p_min={p_min:.3f}. "
            f"Buffer B_eff={b_eff:.4f}."
        )
        lines.append(
            f"Critical entropy H_crit={h_crit:.1f} bits. "
            f"Current H(W)={process_entropy:.2f} bits — "
            f"{'comfortable margin' if process_entropy < 0.5 * h_crit else 'watch closely'}."
        )

    return FeasibilityReport(
        feasible=feasible,
        c_op=c_op,
        p_min=p_min,
        b_eff=b_eff,
        h_crit=h_crit,
        bottleneck_node=bottleneck,
        explanation="\n".join(lines),
    )
