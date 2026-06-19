"""Tests for the task-complexity + tool-misuse model."""

from __future__ import annotations

import pytest

from minimal_oversight import complexity as C


def test_factors_decrease_with_difficulty():
    f = [C.complexity_factor(t) for t in C.complexity_tiers()]
    assert f == sorted(f, reverse=True), "factors must fall as tasks get harder"
    assert C.complexity_factor("trivial") == 1.0
    assert C.complexity_factor("critical") < C.complexity_factor("hard")


def test_default_is_moderate():
    assert C.complexity_factor(None) == C.COMPLEXITY_FACTORS["moderate"]


def test_harder_tasks_lower_effective_competence():
    easy = C.effective_sigma(0.90, "easy")
    hard = C.effective_sigma(0.90, "hard")
    crit = C.effective_sigma(0.90, "critical")
    assert easy > hard > crit


def test_tool_misuse_penalizes():
    clean = C.effective_sigma(0.90, "moderate", tool_misuse=0.0)
    misuse = C.effective_sigma(0.90, "moderate", tool_misuse=0.25)
    assert misuse == pytest.approx(clean * 0.75, rel=1e-9)


def test_effective_sigma_is_clamped():
    assert C.effective_sigma(0.99, "trivial", 0.0) <= 0.99
    assert C.effective_sigma(0.02, "critical", 0.9) >= 0.01


def test_required_prior_inverts_effective():
    # a critical node needing σ_eff=0.80 demands a much higher prior σ
    req = C.required_prior_sigma(0.80, "critical")
    assert C.effective_sigma(req, "critical") == pytest.approx(0.80, rel=1e-9)
    assert req > 0.80, "critical tasks demand stronger raw competence than the bar"


def test_unknown_tier_raises():
    with pytest.raises(ValueError):
        C.complexity_factor("impossible")


def test_bad_misuse_raises():
    with pytest.raises(ValueError):
        C.effective_sigma(0.8, "moderate", tool_misuse=1.5)
