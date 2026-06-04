"""Tests for oversight allocation helpers."""

import numpy as np

from minimal_oversight.allocation import solve_amo, solve_mso


def test_solve_mso_keeps_amo_alias_compatible():
    sigma = np.array([0.30, 0.55, 0.75, 0.90])

    mso = solve_mso(sigma, p_min=0.60)
    amo = solve_amo(sigma, p_min=0.60)

    np.testing.assert_allclose(mso.alpha_star, amo.alpha_star)
    assert mso.delivery == amo.delivery
    assert mso.total_cost == amo.total_cost
