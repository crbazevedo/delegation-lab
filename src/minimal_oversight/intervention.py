"""Intervention: scheduling and monitoring.

Answers: "When should humans step in?" and "What should stop being delegated?"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minimal_oversight import _formulae as F
from minimal_oversight.models import PipelineGraph


class AlertLevel(Enum):
    """Severity of a monitoring alert."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FailureMode(Enum):
    """Diagnostic differential failure modes (Table in Section 4, Demo 3).

    Based on (Δσ_raw, ΔM*) joint movement.
    """

    HEALTHY = "healthy"  # stable / stable
    AGENT_IMPROVING = "agent_improving"  # rising / falling
    MASKING_DEGRADATION = "masking_degradation"  # falling / rising
    CORRELATED_DRIFT = "correlated_drift"  # falling / falling
    CORRECTOR_COASTING = "corrector_coasting"  # stable / rising


@dataclass
class InterventionSchedule:
    """Per-node intervention timing."""

    node_name: str
    t_auto: float
    intervention_frequency: float  # 1 / T*_auto
    review_cost: float
    priority_rank: int


@dataclass
class MonitoringAlert:
    """A monitoring alert triggered by the diagnostic differential."""

    level: AlertLevel
    node_name: str
    failure_mode: FailureMode
    message: str
    recommended_action: str


def compute_autonomy_time(
    c_op: float,
    p_min: float,
    mu_eff: float,
    governance_gap: float = 0.02,
    process_entropy: float = 0.0,
) -> float:
    """Expected time before human intervention is needed.

    T*_auto = B_eff / μ_eff

    Ref: Equation 17.
    """
    return F.autonomy_time(c_op, p_min, governance_gap, process_entropy, mu_eff)


def compute_pipeline_intervention_schedule(
    pipeline: PipelineGraph,
    node_capacities: dict[str, float],
    p_min: float = 0.80,
    governance_gap: float = 0.02,
    process_entropy: float = 0.0,
) -> list[InterventionSchedule]:
    """Compute intervention schedule across all nodes.

    Nodes with short T*_auto need frequent review.
    Nodes with long T*_auto can operate autonomously.
    """
    schedules: list[InterventionSchedule] = []

    for name, node in pipeline.nodes.items():
        c_op_node = node_capacities.get(name, 0.8)
        drift = node.drift_rate if node.drift_rate is not None else 0.005

        t_auto = compute_autonomy_time(
            c_op=c_op_node,
            p_min=p_min,
            mu_eff=drift,
            governance_gap=governance_gap,
            process_entropy=process_entropy,
        )

        freq = 1.0 / t_auto if t_auto > 0 else float("inf")

        schedules.append(InterventionSchedule(
            node_name=name,
            t_auto=t_auto,
            intervention_frequency=freq,
            review_cost=1.0,  # uniform cost for v1
            priority_rank=0,  # assigned after sorting
        ))

    # Sort by T*_auto ascending (most urgent first)
    schedules.sort(key=lambda s: s.t_auto)
    for i, s in enumerate(schedules):
        s.priority_rank = i + 1

    return schedules


def diagnose_failure_mode(
    delta_sigma_raw: float,
    delta_m_star: float,
    threshold: float = 0.01,
) -> FailureMode:
    """Classify the failure mode from the diagnostic differential.

    Based on joint movement of (Δσ_raw, ΔM*):
        stable/stable  → healthy
        rising/falling  → agent improving
        falling/rising  → masking degradation (URGENT)
        falling/falling → correlated drift
        stable/rising   → corrector coasting

    Ref: Section 4, Demonstration 3.
    """
    raw_trend = "stable"
    if delta_sigma_raw > threshold:
        raw_trend = "rising"
    elif delta_sigma_raw < -threshold:
        raw_trend = "falling"

    mask_trend = "stable"
    if delta_m_star > threshold:
        mask_trend = "rising"
    elif delta_m_star < -threshold:
        mask_trend = "falling"

    if raw_trend == "stable" and mask_trend == "stable":
        return FailureMode.HEALTHY
    elif raw_trend == "rising" and mask_trend == "falling":
        return FailureMode.AGENT_IMPROVING
    elif raw_trend == "falling" and mask_trend == "rising":
        return FailureMode.MASKING_DEGRADATION
    elif raw_trend == "falling" and mask_trend == "falling":
        return FailureMode.CORRELATED_DRIFT
    elif raw_trend == "stable" and mask_trend == "rising":
        return FailureMode.CORRECTOR_COASTING
    else:
        return FailureMode.HEALTHY


def check_alerts(
    pipeline: PipelineGraph,
    node_capacities: dict[str, float],
    p_min: float = 0.80,
    masking_threshold: float = 1.5,
    buffer_threshold: float = 0.05,
    governance_gap: float = 0.02,
    process_entropy: float = 0.0,
) -> list[MonitoringAlert]:
    """Check all monitoring conditions and generate alerts.

    Three alert categories:
        1. Masking rising (M* > threshold)
        2. Buffer collapsing (B_eff near zero)
        3. K/N approaching capacity threshold
    """
    alerts: list[MonitoringAlert] = []

    for name, node in pipeline.nodes.items():
        m_star = node.masking_index
        c_op_node = node_capacities.get(name, 0.8)

        # Alert 1: Masking
        if m_star is not None and m_star > masking_threshold:
            alerts.append(MonitoringAlert(
                level=AlertLevel.WARNING if m_star < 2.0 else AlertLevel.CRITICAL,
                node_name=name,
                failure_mode=FailureMode.MASKING_DEGRADATION,
                message=(
                    f"Masking index M*={m_star:.2f} at {name}. "
                    "Corrector is hiding agent weakness."
                ),
                recommended_action=(
                    "Track σ_raw separately. If σ_raw is falling while σ_corr "
                    "is stable, the agent is degrading silently."
                ),
            ))

        # Alert 2: Buffer
        b_eff = F.effective_autonomy_buffer(
            c_op_node, p_min, governance_gap, process_entropy
        )
        if b_eff < buffer_threshold:
            level = AlertLevel.CRITICAL if b_eff <= 0 else AlertLevel.WARNING
            alerts.append(MonitoringAlert(
                level=level,
                node_name=name,
                failure_mode=FailureMode.CORRELATED_DRIFT,
                message=(
                    f"Autonomy buffer B_eff={b_eff:.4f} at {name}. "
                    f"{'Pipeline is past the cliff.' if b_eff <= 0 else 'Near the cliff.'}"
                ),
                recommended_action=(
                    "Simplify routing, increase review capacity, or "
                    "reduce quality target immediately."
                ),
            ))

        # Alert 3: Review capacity
        if (
            node.review_capacity is not None
            and node.sigma_skill is not None
            and node.catch_rate is not None
        ):
            threshold_kn = F.corrector_capacity_threshold(
                p_min, node.sigma_skill, node.catch_rate
            )
            if node.review_capacity < threshold_kn:
                alerts.append(MonitoringAlert(
                    level=AlertLevel.CRITICAL,
                    node_name=name,
                    failure_mode=FailureMode.MASKING_DEGRADATION,
                    message=(
                        f"Review capacity K/N={node.review_capacity:.2f} below "
                        f"threshold {threshold_kn:.2f} at {name}."
                    ),
                    recommended_action=(
                        "Increase corrector capacity or reduce scope. "
                        "Below this threshold, no authority allocation can maintain quality."
                    ),
                ))

    # Sort by severity
    severity_order = {AlertLevel.CRITICAL: 0, AlertLevel.WARNING: 1, AlertLevel.INFO: 2}
    alerts.sort(key=lambda a: severity_order[a.level])

    return alerts


def explain_failure_surface(
    pipeline: PipelineGraph,
    node_capacities: dict[str, float],
    p_min: float = 0.80,
    governance_gap: float = 0.02,
    process_entropy: float = 0.0,
) -> str:
    """Human-readable explanation of the pipeline's failure surface.

    Covers all five failure modes:
        - Infeasible target
        - Masking-driven false confidence
        - Process overload
        - Conditional fragility
        - Upstream bottleneck
    """
    lines: list[str] = []
    lines.append("=== Failure Surface Analysis ===\n")

    from minimal_oversight.capacity import check_feasibility

    report = check_feasibility(
        pipeline, p_min=p_min,
        governance_gap=governance_gap,
        process_entropy=process_entropy,
    )

    # 1. Feasibility
    if not report.feasible:
        lines.append(
            f"[INFEASIBLE TARGET] p_min={p_min:.3f} exceeds C_op={report.c_op:.3f}. "
            "No local governance policy can rescue this design.\n"
        )

    # 2. Masking
    masking_nodes = [
        (name, node.masking_index)
        for name, node in pipeline.nodes.items()
        if node.masking_index is not None and node.masking_index > 1.3
    ]
    if masking_nodes:
        lines.append("[MASKING] Nodes with significant masking (M* > 1.3):")
        for name, m in sorted(masking_nodes, key=lambda x: x[1], reverse=True):
            lines.append(f"  {name}: M*={m:.2f}")
        lines.append(
            "These nodes appear more competent than they are. "
            "Trust σ_raw, not σ_corr, for authorization.\n"
        )

    # 3. Process overload
    if report.b_eff is not None and report.h_crit is not None:
        if process_entropy > 0.7 * report.h_crit:
            lines.append(
                f"[PROCESS OVERLOAD] H(W)={process_entropy:.2f} bits is "
                f"{process_entropy/report.h_crit:.0%} of H_crit={report.h_crit:.1f} bits. "
                "Simplify routing or reduce conditional branching before "
                "adding more review.\n"
            )

    # 4. Upstream bottleneck
    if report.bottleneck_node:
        lines.append(
            f"[BOTTLENECK] {report.bottleneck_node} is the capacity-limiting node. "
            f"Fix upstream before adding downstream checks.\n"
        )

    if len(lines) == 1:
        lines.append("No significant failure modes detected. Pipeline is healthy.\n")

    return "\n".join(lines)
