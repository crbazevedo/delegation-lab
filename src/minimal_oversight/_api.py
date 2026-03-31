"""Flagship API: one-call analysis and recommendations.

This is the front door of the package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from minimal_oversight.allocation import (
    GovernanceRecommendation,
    recommend_governance_changes,
)
from minimal_oversight.capacity import (
    FeasibilityReport,
    check_feasibility,
    compute_pipeline_capacity,
)
from minimal_oversight.estimation import EstimationResult, estimate_node
from minimal_oversight.intervention import (
    InterventionSchedule,
    MonitoringAlert,
    check_alerts,
    compute_pipeline_intervention_schedule,
    explain_failure_surface,
)
from minimal_oversight.models import GovernancePolicy, PipelineGraph, WorkflowTrace
from minimal_oversight.topology import MotifInstance, NodeRisk, detect_motifs, rank_nodes_by_risk


@dataclass
class PipelineReport:
    """Complete analysis of a delegated pipeline.

    This is the output of ``analyze_pipeline()`` — the package's flagship API.
    """

    # Feasibility
    feasibility: FeasibilityReport

    # Per-node estimates
    node_estimates: dict[str, EstimationResult] = field(default_factory=dict)

    # Per-node capacity
    node_capacities: dict[str, float] = field(default_factory=dict)

    # Topology
    motifs: list[MotifInstance] = field(default_factory=list)
    node_risks: list[NodeRisk] = field(default_factory=list)

    # Intervention
    intervention_schedule: list[InterventionSchedule] = field(default_factory=list)
    alerts: list[MonitoringAlert] = field(default_factory=list)

    # Recommendations
    recommendations: list[GovernanceRecommendation] = field(default_factory=list)

    # Failure surface explanation
    failure_explanation: str = ""

    def __str__(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("PIPELINE ANALYSIS REPORT")
        lines.append("=" * 60)

        # Feasibility
        lines.append("\n--- Feasibility ---")
        lines.append(self.feasibility.explanation)

        # Per-node summary
        if self.node_estimates:
            lines.append("\n--- Node Estimates ---")
            lines.append(f"{'Node':<20} {'σ_raw':>8} {'σ_corr':>8} {'M*':>8} {'n':>6}")
            lines.append("-" * 52)
            for name, est in self.node_estimates.items():
                lines.append(
                    f"{name:<20} {est.sigma_raw:>8.3f} {est.sigma_corr:>8.3f} "
                    f"{est.masking_index:>8.2f} {est.sample_size:>6d}"
                )

        # Motifs
        if self.motifs:
            lines.append("\n--- Detected Motifs ---")
            for m in self.motifs:
                lines.append(f"  [{m.motif.value}] {m.risk_description}")

        # Intervention schedule
        if self.intervention_schedule:
            lines.append("\n--- Intervention Schedule ---")
            lines.append(f"{'Rank':<6} {'Node':<20} {'T*_auto':>10} {'Frequency':>10}")
            lines.append("-" * 48)
            for s in self.intervention_schedule[:5]:  # top 5
                freq_str = (
                    f"{s.intervention_frequency:.3f}"
                    if s.intervention_frequency < 100 else "continuous"
                )
                lines.append(
                    f"{s.priority_rank:<6} {s.node_name:<20} "
                    f"{s.t_auto:>10.1f} {freq_str:>10}"
                )

        # Alerts
        if self.alerts:
            lines.append("\n--- Alerts ---")
            for a in self.alerts:
                lines.append(f"  [{a.level.value.upper()}] {a.node_name}: {a.message}")

        # Recommendations
        if self.recommendations:
            lines.append("\n--- Recommendations ---")
            for r in self.recommendations[:5]:  # top 5
                lines.append(f"  {r.priority}. [{r.target_node or 'pipeline'}] {r.action}")
                lines.append(f"     {r.rationale}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


def analyze_pipeline(
    pipeline: PipelineGraph | Any,
    p_min: float = 0.80,
    traces: list[WorkflowTrace] | None = None,
    governance: GovernancePolicy | None = None,
    governance_gap: float = 0.02,
    process_entropy: float = 0.0,
    eta: float = 10.0,
    delta: float = 2.0,
) -> PipelineReport:
    """Analyze a delegated pipeline and produce actionable recommendations.

    This is the flagship API of the package.

    Accepts either a ``PipelineGraph`` or a framework-native object
    (LangGraph StateGraph/CompiledGraph, ADK Agent, or dict config).
    Framework objects are auto-detected and converted.

    Args:
        pipeline: A PipelineGraph, or a LangGraph/ADK object to auto-convert.
        p_min: Minimum acceptable quality target.
        traces: Optional workflow traces for estimation from logs.
        governance: Optional governance policy settings.
        governance_gap: λ — governance gap coefficient (~0.02/bit typical).
        process_entropy: H(W) — estimated process entropy in bits.
        eta: Observation rate (for capacity calculations).
        delta: Decay rate (for capacity calculations).

    Returns:
        PipelineReport with feasibility, estimates, risks, schedule,
        alerts, and recommendations.
    """
    # Auto-detect and convert framework objects
    if not isinstance(pipeline, PipelineGraph):
        pipeline = _auto_convert(pipeline)
    if governance is not None:
        p_min = governance.p_min

    # 1. Estimate from traces (if available)
    node_estimates: dict[str, EstimationResult] = {}
    if traces:
        for name in pipeline.nodes:
            est = estimate_node(name, traces)
            node_estimates[name] = est

            # Update node objects with estimated values
            node = pipeline.get_node(name)
            if node.sigma_raw is None:
                node.sigma_raw = est.sigma_raw
            if node.sigma_corr is None:
                node.sigma_corr = est.sigma_corr
            if node.catch_rate is None and est.catch_rate is not None:
                node.catch_rate = est.catch_rate

    # 2. Compute capacity and fill in missing node signals from theory
    node_capacities = compute_pipeline_capacity(pipeline, eta=eta, delta=delta)

    for name, node in pipeline.nodes.items():
        if node.sigma_raw is None and node.sigma_skill is not None:
            from minimal_oversight._formulae import sigma_raw_fixed_point
            node.sigma_raw = sigma_raw_fixed_point(node.sigma_skill, eta, delta)
        if node.sigma_corr is None and node.sigma_raw is not None:
            c = node.catch_rate if node.catch_rate is not None else 0.65
            from minimal_oversight._formulae import sigma_corr_fixed_point
            node.sigma_corr = sigma_corr_fixed_point(node.sigma_raw, c)

    # 3. Feasibility check
    feasibility = check_feasibility(
        pipeline, p_min=p_min,
        governance_gap=governance_gap,
        process_entropy=process_entropy,
        eta=eta, delta=delta,
    )

    # 4. Topology analysis
    motifs = detect_motifs(pipeline)
    node_risks = rank_nodes_by_risk(pipeline)

    # 5. Intervention schedule
    schedule = compute_pipeline_intervention_schedule(
        pipeline, node_capacities,
        p_min=p_min,
        governance_gap=governance_gap,
        process_entropy=process_entropy,
    )

    # 6. Alerts
    alerts = check_alerts(
        pipeline, node_capacities,
        p_min=p_min,
        governance_gap=governance_gap,
        process_entropy=process_entropy,
    )

    # 7. Recommendations
    recommendations = recommend_governance_changes(
        pipeline, p_min=p_min,
        process_entropy=process_entropy,
        governance_gap=governance_gap,
    )

    # 8. Failure surface
    failure_explanation = explain_failure_surface(
        pipeline, node_capacities,
        p_min=p_min,
        governance_gap=governance_gap,
        process_entropy=process_entropy,
    )

    return PipelineReport(
        feasibility=feasibility,
        node_estimates=node_estimates,
        node_capacities=node_capacities,
        motifs=motifs,
        node_risks=node_risks,
        intervention_schedule=schedule,
        alerts=alerts,
        recommendations=recommendations,
        failure_explanation=failure_explanation,
    )


def _auto_convert(obj: Any) -> PipelineGraph:
    """Auto-detect framework type and convert to PipelineGraph."""
    type_name = type(obj).__name__
    module_name = type(obj).__module__ or ""

    # LangGraph: StateGraph or CompiledGraph
    lg_types = ("StateGraph", "CompiledGraph", "CompiledStateGraph")
    if "langgraph" in module_name or type_name in lg_types:
        from minimal_oversight.connectors.langgraph import from_langgraph
        return from_langgraph(obj)

    # ADK: Agent object
    if "adk" in module_name or "google" in module_name:
        if hasattr(obj, "sub_agents"):
            from minimal_oversight.connectors.adk import from_adk_agent
            return from_adk_agent(obj)

    # Dict config (ADK YAML or generic) — require "sub_agents" key to
    # distinguish ADK configs from arbitrary dicts that happen to have "name".
    if isinstance(obj, dict):
        if "sub_agents" in obj:
            from minimal_oversight.connectors.adk import from_adk_config
            return from_adk_config(obj)

    raise TypeError(
        f"Cannot auto-convert {type_name} to PipelineGraph. "
        f"Pass a PipelineGraph directly, or use a connector: "
        f"from_langgraph(), from_adk_config(), from_adk_agent()."
    )
