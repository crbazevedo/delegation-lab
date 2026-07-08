"""Tracking drifting competence under observation noise (the Kalman variant).

The adaptive controller never sees the true required budget ``r(t)``; it sees a noisy
observation ``r(t) + N(0, sigma^2)``, and ``r(t)`` itself drifts. To stay feasible
(``b >= r``) with probability ``>= 1 - delta`` it must hold a margin above its
estimate, and that margin is pure holding overhead.

For random-walk drift (increment std ``nu``) plus Gaussian observation noise (std
``sigma``) the Kalman filter is the MMSE-optimal causal estimator. Its steady-state
posterior variance ``P*`` is the positive root of ``P^2 + nu^2 P - nu^2 sigma^2 = 0``,
which tends to ``nu * sigma`` for ``nu << sigma``. The matched feasibility margin is
``z_delta * sqrt(P*)``, so every causal controller pays per-step holding overhead at
least ``z_delta * sqrt(P*)`` -- a floor of order ``sqrt(nu * sigma)`` that no filter
removes for ``nu > 0``. The unfiltered deadband (no filtering) pays ``z_delta * sigma``,
a factor ``sqrt(sigma / nu)`` above the floor.

``Z_DELTA_98`` is the one-sided ``Phi^{-1}(0.98)`` used as the default feasibility
level (target infeasibility 2%). The claims are exercised by
``scripts/online_tracking.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Z_DELTA_98 = 2.054  # one-sided Phi^{-1}(0.98)


def kalman_steadystate_var(nu: float, sigma: float) -> float:
    """Steady-state posterior variance ``P*`` of the scalar Kalman filter for
    random-walk drift ``nu`` and observation noise ``sigma`` (the positive Riccati root)."""
    q, r = nu * nu, sigma * sigma
    return (-q + math.sqrt(q * q + 4.0 * q * r)) / 2.0


def matched_margin(p_star: float, z_delta: float = Z_DELTA_98) -> float:
    """Feasibility margin to hold ``b >= r`` w.p. ``>= 1 - delta`` given estimator
    error variance ``p_star``: ``z_delta * sqrt(p_star)``."""
    return z_delta * math.sqrt(p_star)


def noise_floor_per_step(nu: float, sigma: float, z_delta: float = Z_DELTA_98) -> float:
    """Per-step holding-regret floor ``z_delta * sqrt(P*)`` (Kalman-matched). The total
    floor over ``T`` steps is this value times ``T`` = ``Omega(sqrt(nu*sigma) * T)``."""
    return matched_margin(kalman_steadystate_var(nu, sigma), z_delta)


def deadband_margin(sigma: float, z_delta: float = Z_DELTA_98) -> float:
    """Unfiltered deadband margin ``z_delta * sigma`` -- a factor ``sqrt(sigma/nu)``
    above the Kalman-matched floor."""
    return z_delta * sigma


@dataclass
class KalmanTracker:
    """Causal scalar Kalman filter for a random-walk-drifting quantity observed under
    Gaussian noise. Stateful: feed one observation per control step.

    nu     drift increment std (process noise).
    sigma  observation noise std.
    xhat   running estimate (defaults to 0; set to the first observation in practice).
    var    running posterior variance (defaults to ``sigma**2``).
    """

    nu: float
    sigma: float
    xhat: float = 0.0
    var: float = math.nan

    def __post_init__(self) -> None:
        if math.isnan(self.var):
            self.var = self.sigma * self.sigma

    def update(self, obs: float) -> float:
        """Fuse one observation; returns the updated estimate ``xhat``."""
        q, r = self.nu * self.nu, self.sigma * self.sigma
        var_pred = self.var + q
        gain = var_pred / (var_pred + r)
        self.xhat = self.xhat + gain * (obs - self.xhat)
        self.var = (1.0 - gain) * var_pred
        return self.xhat

    def feasible_budget(self, obs: float, z_delta: float = Z_DELTA_98) -> float:
        """Held budget that keeps the node feasible w.h.p.: estimate plus the matched
        margin ``z_delta * sqrt(var)`` after fusing ``obs``."""
        est = self.update(obs)
        return est + z_delta * math.sqrt(self.var)
