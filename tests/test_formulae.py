"""Tests for the private formulae module — the paper's equations."""

import numpy as np
import pytest

from minimal_oversight._formulae import (
    autonomy_time,
    channel_capacity_single_letter,
    corrector_capacity_threshold,
    critical_entropy,
    effective_autonomy_buffer,
    fisher_information,
    masking_index,
    max_pipeline_depth,
    node_capacity,
    optimal_authority,
    recursive_chain_quality,
    return_operator_step,
    sigma_corr_fixed_point,
    sigma_raw_fixed_point,
    solve_lambda,
    sota_priority_score,
)


class TestFisherInformation:
    def test_peaks_at_boundaries(self):
        # Fisher info should be high near 0 and 1
        assert fisher_information(0.05) > fisher_information(0.5)
        assert fisher_information(0.95) > fisher_information(0.5)

    def test_minimum_at_half(self):
        # g(0.5) = 1/(0.5*0.5) = 4, which is the minimum
        assert pytest.approx(fisher_information(0.5), rel=1e-6) == 4.0

    def test_vectorized(self):
        result = fisher_information(np.array([0.3, 0.5, 0.7]))
        assert len(result) == 3


class TestReturnOperator:
    def test_fixed_point_worked_example(self):
        # Conservative σ₀=0 specialization: η=10, δ=2, σ_skill=0.80
        sigma_star = sigma_raw_fixed_point(0.80, eta=10, delta=2)
        assert pytest.approx(sigma_star, rel=1e-3) == 0.667

    def test_fixed_point_with_prior_support(self):
        sigma_star = sigma_raw_fixed_point(0.80, eta=10, delta=2, sigma_0=0.50)
        assert pytest.approx(sigma_star, rel=1e-3) == 0.750

    def test_return_operator_reverts_to_prior(self):
        sigma_next = return_operator_step(
            sigma=0.70,
            sigma_skill_eff=0.70,
            eta=10,
            delta=2,
            dt=0.1,
            sigma_0=0.50,
        )
        assert sigma_next < 0.70

    def test_corrected_fixed_point(self):
        # Paper example: σ*_raw=0.667, c=0.70
        sigma_corr = sigma_corr_fixed_point(0.667, catch_rate=0.70)
        assert pytest.approx(sigma_corr, rel=1e-2) == 0.900

    def test_masking_index_worked_example(self):
        m = masking_index(0.900, 0.667)
        assert pytest.approx(m, rel=1e-2) == 1.35


class TestWaterFilling:
    def test_peaks_at_intermediate_competence(self):
        sigma = np.array([0.30, 0.75, 0.95])
        alpha = optimal_authority(sigma, lam=1.0)
        # Should peak at σ=0.75
        assert alpha[1] > alpha[0]
        assert alpha[1] > alpha[2]

    def test_delivery_constraint(self):
        sigma = np.random.default_rng(42).uniform(0.3, 0.9, size=50)
        p_min = 0.60
        lam = solve_lambda(sigma, p_min)
        alpha = optimal_authority(sigma, lam)
        delivery = np.sum(alpha * sigma) / len(sigma)
        assert delivery >= p_min - 0.01


class TestCapacity:
    def test_single_node(self):
        c = node_capacity(eta=10, delta=2)
        assert pytest.approx(c, rel=1e-3) == 0.833

    def test_chain_quality_decreases_with_depth(self):
        q1 = recursive_chain_quality(1, 0.55, 0.65, 10, 2)
        q3 = recursive_chain_quality(3, 0.55, 0.65, 10, 2)
        q5 = recursive_chain_quality(5, 0.55, 0.65, 10, 2)
        assert q1 > q3 > q5

    def test_channel_capacity_revealed_action_log(self):
        revealed = channel_capacity_single_letter(0.5, 0.2, 0.0)
        hidden = channel_capacity_single_letter(0.5, 0.2, 0.0, action_revealed=False)
        assert pytest.approx(revealed, rel=1e-3) == 0.639
        assert revealed > hidden


class TestAutonomy:
    def test_buffer_positive_when_feasible(self):
        b = effective_autonomy_buffer(c_op=0.86, p_min=0.75, lam=0.02, h_w=2.3)
        assert b > 0

    def test_buffer_negative_when_infeasible(self):
        b = effective_autonomy_buffer(c_op=0.60, p_min=0.80, lam=0.02, h_w=0.0)
        assert b < 0

    def test_autonomy_time_inversely_proportional_to_drift(self):
        t1 = autonomy_time(0.86, 0.75, 0.02, 2.0, mu_eff=0.005)
        t2 = autonomy_time(0.86, 0.75, 0.02, 2.0, mu_eff=0.010)
        assert pytest.approx(t1 / t2, rel=0.1) == 2.0

    def test_critical_entropy(self):
        h = critical_entropy(c_op=0.80, p_min=0.50, lam=0.02)
        assert pytest.approx(h, rel=1e-3) == 15.0


class TestMaxDepth:
    def test_worked_example(self):
        # Recursive corrected-chain definition: D=1 clears 0.80, D=2 does not.
        d = max_pipeline_depth(0.55, 0.65, 0.80)
        assert d == 1.0

    def test_low_target_has_no_finite_depth_cliff(self):
        d = max_pipeline_depth(0.55, 0.65, 0.50, max_depth=20)
        assert np.isinf(d)


class TestCorrectorCapacity:
    def test_threshold_uses_raw_fixed_point(self):
        threshold = corrector_capacity_threshold(0.80, sigma_raw_star=0.60, catch_rate=0.50)
        assert pytest.approx(threshold, rel=1e-3) == 1.0

    def test_threshold_is_zero_when_raw_support_suffices(self):
        threshold = corrector_capacity_threshold(0.50, sigma_raw_star=0.60, catch_rate=0.50)
        assert threshold == 0.0


class TestSOTA:
    def test_score_increases_with_centrality(self):
        s1 = sota_priority_score(1.0, 1.35, 0.45)
        s2 = sota_priority_score(3.0, 1.35, 0.45)
        assert s2 > s1
