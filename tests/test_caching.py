"""Shared-pool caching: LRU is Theta(h)-competitive, MARKER O(log h), ratchet infeasible."""

import numpy as np
import pytest

from minimal_oversight.caching import (
    SharedPoolController,
    competitive_ratio,
    cyclic_adversary,
    lru_misses,
    pool_capacity,
    ratchet_demand,
)


def test_pool_capacity():
    assert pool_capacity(2.0, 1.0) == 2
    assert pool_capacity(5.0, 2.0) == 2
    with pytest.raises(ValueError):
        pool_capacity(1.0, 0.0)


def test_lru_is_theta_h_on_adversary():
    for h in (2, 3, 4, 6, 8):
        req = cyclic_adversary(h, 200)
        cr = competitive_ratio("lru", req, h)
        assert cr == pytest.approx(h, rel=0.10)   # CR tracks the pool size h


def test_marker_beats_lru_by_log_h():
    for h in (8, 16):
        req = cyclic_adversary(h, 400)
        lru_cr = competitive_ratio("lru", req, h)
        mk = float(np.mean([competitive_ratio("marker", req, h, seed=s) for s in range(8)]))
        harmonic = float(np.sum(1.0 / np.arange(1, h + 1)))
        assert mk < lru_cr                          # exponential improvement
        assert mk == pytest.approx(harmonic, rel=0.30)


def test_ratchet_is_infeasible_above_h():
    h = 4
    req = cyclic_adversary(h, 6)                     # h + 1 = 5 distinct sinks
    assert ratchet_demand(req) == h + 1
    assert ratchet_demand(req) > h                  # demands more than the pool: infeasible


def test_controller_matches_lru_misses():
    rng = np.random.default_rng(0)
    req = [int(x) for x in rng.integers(0, 7, size=500)]
    h = 3
    ctrl = SharedPoolController(h, policy="lru")
    for s in req:
        ctrl.request(s)
    assert ctrl.misses == lru_misses(req, h)
