"""Estimation: infer framework quantities from logs.

This is the most useful module in practice. Given workflow traces,
it produces the signals the rest of the package operates on.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from minimal_oversight.models import Node, PipelineGraph, WorkflowTrace


@dataclass
class EstimationResult:
    """Estimated quantities for a single node."""

    node_name: str
    sigma_raw: float
    sigma_corr: float
    masking_index: float
    catch_rate: float | None
    sample_size: int
    ci_sigma_raw: tuple[float, float] | None = None
    ci_sigma_corr: tuple[float, float] | None = None


def estimate_sigma_raw(
    outcomes: list[float] | np.ndarray,
    window: int | None = None,
) -> float:
    """Estimate raw competence from pre-correction outcomes.

    Args:
        outcomes: Sequence of binary outcomes (1 = correct, 0 = error).
        window: If set, use only the last *window* observations (sliding window).
    """
    arr = np.asarray(outcomes, dtype=float)
    if window is not None and len(arr) > window:
        arr = arr[-window:]
    if len(arr) == 0:
        return 0.0
    return float(np.mean(arr))


def estimate_sigma_corr(
    corrected_outcomes: list[float] | np.ndarray,
    window: int | None = None,
) -> float:
    """Estimate corrected quality from post-correction outcomes.

    Args:
        corrected_outcomes: Sequence of binary outcomes after correction.
        window: If set, use only the last *window* observations.
    """
    return estimate_sigma_raw(corrected_outcomes, window=window)


def estimate_masking_index(sigma_corr: float, sigma_raw: float) -> float:
    """M* = σ_corr / σ_raw."""
    if sigma_raw <= 0:
        return float("inf")
    return sigma_corr / sigma_raw


def estimate_catch_rate(
    raw_outcomes: list[float] | np.ndarray,
    corrected_outcomes: list[float] | np.ndarray,
) -> float | None:
    """Infer corrector catch rate from paired pre/post-correction outcomes.

    c = (σ_corr − σ_raw) / (1 − σ_raw)

    Returns None if σ_raw ≈ 1 (no errors to catch).
    """
    s_raw = float(np.mean(raw_outcomes))
    s_corr = float(np.mean(corrected_outcomes))
    if (1.0 - s_raw) < 1e-8:
        return None
    c = (s_corr - s_raw) / (1.0 - s_raw)
    return float(np.clip(c, 0.0, 1.0))


def estimate_process_entropy(
    traces: list[WorkflowTrace],
    pipeline: PipelineGraph,
) -> float:
    """Estimate process entropy H(W) from routing and timing traces.

    H(W) = H(routing) + H(tool calls) + H(timing)

    Simplified v1: estimates routing entropy from the distribution of
    routing paths observed in traces.

    Ref: Equation 14.
    """
    if not traces:
        return 0.0

    # Count routing path frequencies
    path_counts: dict[str, int] = {}
    for trace in traces:
        path_key = "->".join(trace.routing_path)
        path_counts[path_key] = path_counts.get(path_key, 0) + 1

    total = sum(path_counts.values())
    if total == 0:
        return 0.0

    probs = np.array([c / total for c in path_counts.values()])
    probs = probs[probs > 0]
    entropy = -float(np.sum(probs * np.log2(probs)))
    return entropy


def estimate_drift(
    outcomes: list[float] | np.ndarray,
    window_size: int = 50,
    step: int = 10,
) -> float:
    """Estimate drift rate μ_eff from a rolling window over outcomes.

    Fits a linear trend to windowed σ_raw estimates and returns the
    slope (negative = degradation).
    """
    arr = np.asarray(outcomes, dtype=float)
    if len(arr) < 2 * window_size:
        return 0.0

    means = []
    positions = []
    for i in range(0, len(arr) - window_size + 1, step):
        means.append(float(np.mean(arr[i : i + window_size])))
        positions.append(i + window_size / 2)

    if len(means) < 2:
        return 0.0

    slope, _ = np.polyfit(positions, means, 1)
    return float(-slope)  # positive drift_rate means degradation


def estimate_noise(
    outcomes: list[float] | np.ndarray,
    window_size: int = 50,
    step: int = 10,
) -> float:
    """Estimate noise variance ν²_eff from rolling window variance."""
    arr = np.asarray(outcomes, dtype=float)
    if len(arr) < 2 * window_size:
        return 0.0

    variances = []
    for i in range(0, len(arr) - window_size + 1, step):
        variances.append(float(np.var(arr[i : i + window_size])))

    if not variances:
        return 0.0
    return float(np.mean(variances))


def bootstrap_ci(
    outcomes: list[float] | np.ndarray,
    n_resamples: int = 10_000,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Bootstrap confidence interval for a mean estimate."""
    arr = np.asarray(outcomes, dtype=float)
    rng = np.random.default_rng()
    boot_means = np.array([
        float(np.mean(rng.choice(arr, size=len(arr), replace=True)))
        for _ in range(n_resamples)
    ])
    alpha = (1 - confidence) / 2
    lo = float(np.quantile(boot_means, alpha))
    hi = float(np.quantile(boot_means, 1 - alpha))
    return (lo, hi)


def estimate_node(
    node_name: str,
    traces: list[WorkflowTrace],
    window: int | None = None,
    bootstrap: bool = False,
) -> EstimationResult:
    """Estimate all framework quantities for a single node from traces.

    This is the workhorse function for the estimation module.
    """
    raw_outcomes = [
        t.node_outcomes[node_name]
        for t in traces
        if node_name in t.node_outcomes
    ]
    corr_outcomes = [
        t.node_corrected[node_name]
        for t in traces
        if node_name in t.node_corrected
    ]

    s_raw = estimate_sigma_raw(raw_outcomes, window=window) if raw_outcomes else 0.0
    s_corr = estimate_sigma_corr(corr_outcomes, window=window) if corr_outcomes else 0.0
    m_star = estimate_masking_index(s_corr, s_raw)
    c_hat = (
        estimate_catch_rate(raw_outcomes, corr_outcomes)
        if raw_outcomes and corr_outcomes
        else None
    )

    ci_raw = None
    ci_corr = None
    if bootstrap and raw_outcomes:
        ci_raw = bootstrap_ci(raw_outcomes)
    if bootstrap and corr_outcomes:
        ci_corr = bootstrap_ci(corr_outcomes)

    return EstimationResult(
        node_name=node_name,
        sigma_raw=s_raw,
        sigma_corr=s_corr,
        masking_index=m_star,
        catch_rate=c_hat,
        sample_size=len(raw_outcomes),
        ci_sigma_raw=ci_raw,
        ci_sigma_corr=ci_corr,
    )
