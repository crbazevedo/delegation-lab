"""Ski-rental structure of the online review-release decision.

When a reviewed node recovers and its review budget is no longer needed, an online
controller faces rent-or-buy. *Holding* the now-idle budget costs ``b`` per step
(rent); *releasing* it and re-acquiring it if the node becomes the bottleneck again
costs ``2 * lambda * b`` (buy: one ``lambda`` to release, one to re-add). The slack
duration is unknown, so the hold-vs-release decision is exactly online ski-rental.

The hysteresis dwell timer of
:func:`minimal_oversight.online_control.online_step_release` is the ski-rental
threshold. The optimal dwell is ``dwell* = 2 * lambda`` and achieves competitive
ratio ``2 - 1/(2*lambda) < 2``; no deterministic dwell does better against an
adversarial slack length (the classical deterministic ski-rental lower bound).

This module gives the threshold helper and the per-slack-phase closed forms used to
verify the ratio. The numbers are exercised end-to-end by
``scripts/online_skirental.py``.
"""

from __future__ import annotations


def skirental_dwell(lam: float) -> float:
    """Optimal (minimax) release dwell: hold a slack node ``2 * lambda`` steps before
    releasing it. This is the rent-cumulative-equals-buy break-even point."""
    return 2.0 * lam


def skirental_ratio(lam: float) -> float:
    """Competitive ratio of the optimal dwell ``2 * lambda``: ``2 - 1/(2*lambda)``."""
    return 2.0 - 1.0 / (2.0 * lam)


def opt_slack_cost(tau: float, lam: float, b: float = 1.0) -> float:
    """Clairvoyant cost over one slack phase of (known) length ``tau``: hold through
    short slack, release at once through long slack -> ``b * min(tau, 2*lambda)``."""
    return b * min(tau, 2.0 * lam)


def dwell_slack_cost(tau: float, lam: float, d: float, b: float = 1.0) -> float:
    """Cost of a fixed dwell-``d`` policy over a slack phase of length ``tau``.

    If ``d <= tau`` the policy rents ``d - 1`` steps and then buys (release + re-add);
    otherwise the slack ends before the dwell elapses and it holds throughout.
    """
    if d <= tau:
        return b * ((d - 1) + 2.0 * lam)
    return b * tau


def worst_case_ratio(d: float, lam: float, tau_max: int = 1000, b: float = 1.0) -> float:
    """Worst-case competitive ratio of dwell ``d`` over slack lengths ``tau in [1, tau_max]``."""
    worst = 0.0
    for tau in range(1, tau_max + 1):
        worst = max(worst, dwell_slack_cost(tau, lam, d, b) / opt_slack_cost(tau, lam, b))
    return worst


def minimax_dwell(lam: float, candidates: list[float] | None = None,
                  tau_max: int = 1000) -> tuple[float, float]:
    """Return ``(dwell*, worst_case_ratio)`` minimizing the worst-case ratio over the
    candidate dwells (defaults to a sweep bracketing ``2*lambda``)."""
    if candidates is None:
        candidates = sorted({1.0, lam, 1.5 * lam, 2.0 * lam, 2.5 * lam, 4.0 * lam})
    best_d, best = candidates[0], float("inf")
    for d in candidates:
        w = worst_case_ratio(d, lam, tau_max)
        if w < best:
            best, best_d = w, d
    return best_d, best
