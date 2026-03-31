"""Visualization: dashboards and plots for governed delegation.

Most practitioners will understand the framework through these.
"""

from __future__ import annotations

from typing import Any

import numpy as np

# Lazy imports for optional viz dependencies
_MPL_AVAILABLE = False
_PLOTLY_AVAILABLE = False


def _ensure_matplotlib() -> Any:
    global _MPL_AVAILABLE
    try:
        import matplotlib.pyplot as plt
        _MPL_AVAILABLE = True
        return plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for visualization. "
            "Install with: pip install minimal-oversight[viz]"
        )


def plot_masking_dashboard(
    node_names: list[str],
    sigma_raw: list[float],
    sigma_corr: list[float],
    masking_threshold: float = 1.3,
    figsize: tuple[float, float] = (12, 5),
) -> Any:
    """Side-by-side bar chart of σ_raw vs σ_corr with masking index.

    Nodes with M* > threshold are highlighted.
    """
    plt = _ensure_matplotlib()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    x = np.arange(len(node_names))
    width = 0.35

    # Left: dual sigma bars
    ax1.bar(x - width / 2, sigma_raw, width, label="σ_raw", color="#e74c3c", alpha=0.8)
    ax1.bar(x + width / 2, sigma_corr, width, label="σ_corr", color="#2ecc71", alpha=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(node_names, rotation=45, ha="right")
    ax1.set_ylabel("Quality")
    ax1.set_title("Raw Competence vs Corrected Quality")
    ax1.legend()
    ax1.set_ylim(0, 1.05)

    # Right: masking index
    m_star = [sc / sr if sr > 0 else 0 for sr, sc in zip(sigma_raw, sigma_corr)]
    colors = ["#e74c3c" if m > masking_threshold else "#3498db" for m in m_star]
    ax2.bar(x, m_star, color=colors, alpha=0.8)
    ax2.axhline(y=1.0, color="gray", linestyle="--", alpha=0.5, label="M*=1 (no masking)")
    ax2.axhline(
        y=masking_threshold, color="#e74c3c", linestyle="--", alpha=0.5,
        label=f"M*={masking_threshold} (threshold)",
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(node_names, rotation=45, ha="right")
    ax2.set_ylabel("M* (masking index)")
    ax2.set_title("Masking Index per Node")
    ax2.legend()

    fig.tight_layout()
    return fig


def plot_autonomy_buffer(
    c_op: float,
    p_min: float,
    governance_gap: float,
    h_w_range: np.ndarray | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Plot autonomy buffer B_eff as a function of process entropy H(W).

    Shows the capacity cliff at H_crit.
    """
    plt = _ensure_matplotlib()

    if h_w_range is None:
        h_crit = (c_op - p_min) / governance_gap if governance_gap > 0 else 10.0
        h_w_range = np.linspace(0, h_crit * 1.3, 200)

    b_eff = c_op - p_min - governance_gap * h_w_range
    h_crit = (c_op - p_min) / governance_gap if governance_gap > 0 else float("inf")

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(h_w_range, b_eff, "b-", linewidth=2, label="B_eff")
    ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)
    ax.axvline(x=h_crit, color="#e74c3c", linestyle="--", alpha=0.7, label=f"H_crit={h_crit:.1f}")
    ax.fill_between(h_w_range, b_eff, 0, where=b_eff > 0, alpha=0.15, color="blue")
    ax.fill_between(h_w_range, b_eff, 0, where=b_eff <= 0, alpha=0.15, color="red")

    ax.set_xlabel("Process entropy H(W) [bits]")
    ax.set_ylabel("Effective autonomy buffer B_eff")
    ax.set_title(f"Autonomy Buffer (C_op={c_op:.2f}, p_min={p_min:.2f}, λ={governance_gap})")
    ax.legend()
    fig.tight_layout()
    return fig


def plot_pipeline_risk(
    node_names: list[str],
    sota_scores: list[float],
    masking_indices: list[float],
    figsize: tuple[float, float] = (10, 5),
) -> Any:
    """Horizontal bar chart ranking nodes by governance priority.

    Combines SOTA score with masking index annotation.
    """
    plt = _ensure_matplotlib()

    fig, ax = plt.subplots(figsize=figsize)

    # Sort by SOTA score
    order = np.argsort(sota_scores)[::-1]
    names_sorted = [node_names[i] for i in order]
    scores_sorted = [sota_scores[i] for i in order]
    masking_sorted = [masking_indices[i] for i in order]

    colors = [
        "#e74c3c" if m > 1.5 else "#f39c12" if m > 1.2 else "#27ae60"
        for m in masking_sorted
    ]

    y_pos = np.arange(len(names_sorted))
    ax.barh(y_pos, scores_sorted, color=colors, alpha=0.8)

    # Annotate with M*
    for i, (score, m) in enumerate(zip(scores_sorted, masking_sorted)):
        ax.text(score + 0.01 * max(scores_sorted), i, f"M*={m:.2f}", va="center", fontsize=9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names_sorted)
    ax.set_xlabel("SOTA Priority Score S(v)")
    ax.set_title("Node Governance Priority Ranking")
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


def plot_scope_frontier(
    sigma_raw: np.ndarray,
    p_min: float,
    coverage_range: np.ndarray | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Coverage-cost frontier plot.

    Shows how total governance cost increases with required coverage,
    and how average delegated competence decreases.
    """
    plt = _ensure_matplotlib()
    from minimal_oversight.allocation import solve_amo

    sigma = np.asarray(sigma_raw, dtype=float)
    n = len(sigma)

    if coverage_range is None:
        coverage_range = np.linspace(0.1, 1.0, 20)

    costs = []
    avg_sigmas = []
    counts = []

    # Sort by cost-effectiveness
    eps = 1e-10
    s = np.clip(sigma, eps, 1.0 - eps)
    effectiveness = s * np.sqrt(s * (1 - s))
    order = np.argsort(-effectiveness)

    for cov in coverage_range:
        k = max(1, int(np.ceil(cov * n)))
        selected = order[:k]
        sel_sigma = sigma[selected]

        try:
            result = solve_amo(sel_sigma, p_min)
            costs.append(result.total_cost)
        except Exception:
            costs.append(float("nan"))

        avg_sigmas.append(float(np.mean(sel_sigma)))
        counts.append(k)

    fig, ax1 = plt.subplots(figsize=figsize)
    ax2 = ax1.twinx()

    ax1.plot(coverage_range * 100, costs, "b-o", markersize=4, label="Total cost")
    ax2.plot(coverage_range * 100, avg_sigmas, "r--s", markersize=4, label="Avg σ_raw")

    ax1.set_xlabel("Coverage requirement (%)")
    ax1.set_ylabel("Total governance cost", color="blue")
    ax2.set_ylabel("Average σ_raw of delegated tasks", color="red")
    ax1.set_title("Coverage-Cost Frontier")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right")

    fig.tight_layout()
    return fig
