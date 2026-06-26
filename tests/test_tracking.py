"""Kalman tracking: the noise floor is fundamental (Omega(sqrt(nu*sigma))) and matched."""

import math

import numpy as np
import pytest

from minimal_oversight.tracking import (
    Z_DELTA_98,
    KalmanTracker,
    deadband_margin,
    kalman_steadystate_var,
    noise_floor_per_step,
)


def test_steadystate_is_riccati_root():
    for nu, sigma in [(0.02, 0.20), (0.01, 0.40), (0.04, 0.10)]:
        p = kalman_steadystate_var(nu, sigma)
        assert p > 0
        assert abs(p * p + nu * nu * p - nu * nu * sigma * sigma) < 1e-12


def test_small_drift_limit_is_sqrt_nu_sigma():
    nu, sigma = 1e-4, 1.0
    p = kalman_steadystate_var(nu, sigma)
    assert math.sqrt(p) == pytest.approx(math.sqrt(nu * sigma), rel=0.02)


def _sim(nu, sigma, n=20000, seed=11):
    rng = np.random.default_rng(seed)
    r = np.cumsum(rng.normal(0.0, nu, n))
    obs = r + rng.normal(0.0, sigma, n)
    return r, obs


def test_kalman_matches_floor_and_beats_naive_estimators():
    nu, sigma, burn = 0.02, 0.20, 2000
    r, obs = _sim(nu, sigma)
    kt = KalmanTracker(nu, sigma, xhat=float(obs[0]))
    est = np.array([kt.update(float(o)) for o in obs])
    kal = math.sqrt(np.mean((est[burn:] - r[burn:]) ** 2))
    assert kal == pytest.approx(math.sqrt(kalman_steadystate_var(nu, sigma)), rel=0.05)
    # an EWMA and the raw observation cannot beat the MMSE-optimal Kalman estimate
    x, ew = float(obs[0]), []
    for o in obs:
        x = 0.2 * o + 0.8 * x
        ew.append(x)
    ew = np.array(ew)
    assert kal <= math.sqrt(np.mean((ew[burn:] - r[burn:]) ** 2)) + 1e-9
    assert kal < math.sqrt(np.mean((obs[burn:] - r[burn:]) ** 2))


def test_floor_scales_as_sqrt_nu_sigma():
    z = Z_DELTA_98
    ratios = [
        noise_floor_per_step(nu, sigma, z) / (z * math.sqrt(nu * sigma))
        for nu, sigma in [(0.01, 0.1), (0.01, 0.4), (0.04, 0.1), (0.04, 0.4), (0.02, 0.2)]
    ]
    assert max(ratios) / min(ratios) < 1.3


def test_deadband_is_sqrt_sigma_over_nu_above_floor():
    nu, sigma = 0.001, 0.20
    gap = deadband_margin(sigma) / noise_floor_per_step(nu, sigma)
    assert gap == pytest.approx(math.sqrt(sigma / nu), rel=0.05)
