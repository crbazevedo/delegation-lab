"""Allocation: optimization and policy support.

Answers: "Where should I place review effort?" and "What should change?"
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from minimal_oversight import _formulae as F
from minimal_oversight.models import PipelineGraph
from minimal_oversight.topology import delegation_centrality


@dataclass
class AllocationResult:
    """Result of the AMO water-filling optimization."""

    alpha_star: np.ndarray
    sigma_raw: np.ndarray
    lam: float
    total_cost: float
    delivery: float


@dataclass
class ScopeRecommendation:
    """Recommendation on which tasks should remain delegated."""

    delegated_tasks: list[int]
    excluded_tasks: list[int]
    coverage: float
    total_cost: float
    avg_sigma_delegated: float
    explanation: str


@dataclass
class GovernanceRecommendation:
    """A single actionable recommendation."""

    priority: int
    action: str
    target_node: str | None
    rationale: str
    expected_impact: str


def solve_amo(
    sigma_raw: np.ndarray,
    p_min: float,
    alpha_max: float = 1.0,
) -> AllocationResult:
    """Solve the Axiom of Minimal Oversight for optimal authority allocation.

    Finds the water-filling solution α*(x) that minimizes governance cost
    subject to the delivery constraint.

    Args:
        sigma_raw: Raw competence across scope points.
        p_min: Minimum quality target (delivery constraint).
        alpha_max: Maximum authority at any point.

    Returns:
        AllocationResult with optimal α* and supporting quantities.
    """
    sigma = np.asarray(sigma_raw, dtype=float)
    lam = F.solve_lambda(sigma, p_min, alpha_max)
    alpha_star = F.optimal_authority(sigma, lam, alpha_max)

    # Governance cost: ∫ α² √g dx
    vol = F.fisher_volume_element(sigma)
    total_cost = float(np.sum(alpha_star**2 * vol))
    delivery = float(np.sum(alpha_star * sigma))

    return AllocationResult(
        alpha_star=alpha_star,
        sigma_raw=sigma,
        lam=lam,
        total_cost=total_cost,
        delivery=delivery,
    )


def select_scope(
    sigma_raw: np.ndarray,
    p_min: float,
    coverage_min: float = 0.0,
    alpha_max: float = 1.0,
) -> ScopeRecommendation:
    """Endogenous scope selection: which tasks should be delegated?

    Without coverage constraint, the optimizer cherry-picks the easiest tasks.
    With coverage_min, it forces broader delegation.

    Args:
        sigma_raw: Raw competence for each candidate task.
        p_min: Quality target per delegated task.
        coverage_min: Minimum fraction of tasks that must be delegated [0, 1].
        alpha_max: Maximum authority ceiling.
    """
    sigma = np.asarray(sigma_raw, dtype=float)
    n = len(sigma)

    # Cost-effectiveness: σ · √(σ(1−σ)) — peaks at σ ≈ 0.75
    eps = 1e-10
    s = np.clip(sigma, eps, 1.0 - eps)
    effectiveness = s * np.sqrt(s * (1 - s))
    order = np.argsort(-effectiveness)  # most cost-effective first

    # Greedy: add tasks in order of cost-effectiveness until coverage met
    min_count = max(1, int(np.ceil(coverage_min * n)))
    delegated = list(order[:min_count])

    # Extend to additional tasks if they're above p_min threshold
    for idx in order[min_count:]:
        if sigma[idx] >= p_min * 0.8:  # heuristic: delegate if reasonably competent
            delegated.append(idx)

    delegated_set = set(delegated)
    excluded = [i for i in range(n) if i not in delegated_set]

    # Solve AMO over delegated subset
    if delegated:
        delegated_sigma = sigma[delegated]
        result = solve_amo(delegated_sigma, p_min, alpha_max)
        total_cost = result.total_cost
    else:
        total_cost = 0.0

    avg_sigma = float(np.mean(sigma[delegated])) if delegated else 0.0

    return ScopeRecommendation(
        delegated_tasks=sorted(delegated),
        excluded_tasks=sorted(excluded),
        coverage=len(delegated) / n if n > 0 else 0.0,
        total_cost=total_cost,
        avg_sigma_delegated=avg_sigma,
        explanation=(
            f"Delegating {len(delegated)}/{n} tasks "
            f"(coverage {len(delegated)/n:.0%}). "
            f"Average competence of delegated tasks: {avg_sigma:.3f}. "
            f"Total governance cost: {total_cost:.3f}."
        ),
    )


def prioritize_intervention(
    pipeline: PipelineGraph,
) -> list[GovernanceRecommendation]:
    """Rank nodes by where additional review effort has the most impact.

    Uses the SOTA proxy S(v) = DC(v) × M*(v) × κ(v) when exact
    sensitivities are unavailable.
    """
    recommendations: list[GovernanceRecommendation] = []

    for name, node in pipeline.nodes.items():
        dc = delegation_centrality(pipeline, name)
        m_star = node.masking_index
        sigma_skill = node.sigma_skill

        if m_star is None or sigma_skill is None:
            continue

        kappa = 1.0 - sigma_skill
        sota = F.sota_priority_score(dc, m_star, kappa)

        # Determine recommended action based on node profile
        if m_star > 1.5 and dc > 1.0:
            action = "Increase review capacity at this node"
            rationale = (
                f"High masking (M*={m_star:.2f}) at a high-centrality node (DC={dc:.1f}). "
                "The corrector is hiding weakness that propagates downstream."
            )
            impact = "Reduces downstream error propagation"
        elif m_star > 1.5:
            action = "Add monitoring for raw competence"
            rationale = (
                f"Masking index M*={m_star:.2f} suggests corrector is doing heavy lifting. "
                "Track σ_raw separately to detect silent degradation."
            )
            impact = "Early warning of competence loss"
        elif kappa > 0.5 and dc > 1.0:
            action = "Upgrade agent at this node"
            rationale = (
                f"Low skill (σ={sigma_skill:.2f}) at a high-leverage point (DC={dc:.1f}). "
                "Improving the agent here has outsized downstream impact."
            )
            impact = "Raises effective skill for all downstream nodes"
        else:
            action = "Monitor — no urgent action"
            rationale = f"Node is performing adequately (σ={sigma_skill:.2f}, M*={m_star:.2f})."
            impact = "Stable"

        recommendations.append(GovernanceRecommendation(
            priority=0,  # will be set after sorting
            action=action,
            target_node=name,
            rationale=rationale,
            expected_impact=impact,
        ))

    # Sort by SOTA score descending and assign priorities
    recommendations.sort(
        key=lambda r: F.sota_priority_score(
            delegation_centrality(pipeline, r.target_node or ""),
            pipeline.get_node(r.target_node or "").masking_index or 1.0,
            1.0 - (pipeline.get_node(r.target_node or "").sigma_skill or 0.5),
        ),
        reverse=True,
    )
    for i, rec in enumerate(recommendations):
        rec.priority = i + 1

    return recommendations


def recommend_governance_changes(
    pipeline: PipelineGraph,
    p_min: float = 0.80,
    process_entropy: float = 0.0,
    governance_gap: float = 0.02,
) -> list[GovernanceRecommendation]:
    """High-level governance recommendations for a pipeline.

    Combines capacity analysis, topology, and intervention priority
    into an ordered list of actionable changes.
    """
    from minimal_oversight.capacity import check_feasibility

    report = check_feasibility(
        pipeline, p_min=p_min,
        governance_gap=governance_gap,
        process_entropy=process_entropy,
    )
    recs = prioritize_intervention(pipeline)

    # Add structural recommendations
    if not report.feasible:
        recs.insert(0, GovernanceRecommendation(
            priority=0,
            action="Redesign pipeline — target quality is infeasible",
            target_node=report.bottleneck_node,
            rationale=report.explanation,
            expected_impact="Required before any governance policy can help",
        ))

    if report.b_eff is not None and report.b_eff < 0.05 and report.feasible:
        recs.insert(0 if report.feasible else 1, GovernanceRecommendation(
            priority=0,
            action="Reduce workflow complexity or increase review capacity",
            target_node=None,
            rationale=(
                f"Autonomy buffer B_eff={report.b_eff:.4f} is dangerously thin. "
                "Pipeline is near the autonomy cliff."
            ),
            expected_impact="Prevents collapse under minor perturbation",
        ))

    # Re-number priorities
    for i, rec in enumerate(recs):
        rec.priority = i + 1

    return recs
