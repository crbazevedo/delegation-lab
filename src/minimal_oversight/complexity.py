"""Task complexity and tool-misuse — how a node's *demand* meets a model's competence.

A prior (model × task-type) gives raw competence for a *typical* instance. A real
node is harder or easier than typical, and a tool-using node can *misuse* its
tools. Both lower the competence actually achieved at that node:

    σ_eff = σ_prior · complexity_factor · (1 − tool_misuse)

So a **critical** task drives σ_eff down — you need a stronger model to clear the
same bar, which is why hard/critical tasks tend to require proprietary frontier
models while easy tasks are comfortably served by cheap open-source ones.

This module is pure: it knows nothing about cost or the graph. The optimizer
(:mod:`minimal_oversight.optimize`) combines it with the priors and the registry.
"""

from __future__ import annotations

# Closed enum of complexity tiers → competence multiplier. Ordered easy→hard.
COMPLEXITY_FACTORS: dict[str, float] = {
    "trivial": 1.00,    # boilerplate; a typical instance or easier
    "easy": 0.95,
    "moderate": 0.85,   # the default — "a typical instance of this task"
    "hard": 0.72,
    "critical": 0.58,   # high-stakes / adversarial / long-tail; few models clear it
}

DEFAULT_COMPLEXITY = "moderate"


def complexity_factor(complexity: str | None) -> float:
    """Multiplier for a complexity tier (defaults to ``moderate``)."""
    if complexity is None:
        complexity = DEFAULT_COMPLEXITY
    try:
        return COMPLEXITY_FACTORS[complexity]
    except KeyError:
        raise ValueError(
            f"unknown complexity {complexity!r}; "
            f"expected one of {sorted(COMPLEXITY_FACTORS)}"
        ) from None


def _clamp(x: float, lo: float = 0.01, hi: float = 0.99) -> float:
    return max(lo, min(hi, x))


def effective_sigma(
    prior_sigma: float,
    complexity: str | None = DEFAULT_COMPLEXITY,
    tool_misuse: float = 0.0,
) -> float:
    """Competence a model actually achieves at a node.

    Args:
        prior_sigma: The model's raw competence on a typical instance of the
            task (from the priors table).
        complexity: Task complexity tier (see :data:`COMPLEXITY_FACTORS`).
        tool_misuse: P(the node calls a tool wrongly / unsafely) in [0, 1] — a
            multiplicative penalty for tool/MCP-using nodes.

    Returns:
        σ_eff = prior_sigma · complexity_factor · (1 − tool_misuse), clamped.
    """
    if not (0.0 <= tool_misuse <= 1.0):
        raise ValueError(f"tool_misuse must be in [0,1], got {tool_misuse}")
    eff = prior_sigma * complexity_factor(complexity) * (1.0 - tool_misuse)
    return _clamp(eff)


def required_prior_sigma(
    target_sigma: float,
    complexity: str | None = DEFAULT_COMPLEXITY,
    tool_misuse: float = 0.0,
) -> float:
    """Invert :func:`effective_sigma`: the *prior* σ a model needs to clear a bar.

    To achieve ``target_sigma`` at a node of this complexity (and tool misuse),
    a model must have prior competence ≥ this value. Used by the optimizer to
    filter the candidate models that "make the cut" for a node.
    """
    denom = complexity_factor(complexity) * (1.0 - tool_misuse)
    if denom <= 0:
        return float("inf")
    return target_sigma / denom


def complexity_tiers() -> list[str]:
    """Tiers ordered easy → hard."""
    return list(COMPLEXITY_FACTORS)
