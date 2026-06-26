"""Ski-rental release: the optimal dwell is 2*lambda and is 2-1/(2*lambda)-competitive."""

import pytest

from minimal_oversight.skirental import (
    dwell_slack_cost,
    minimax_dwell,
    opt_slack_cost,
    skirental_dwell,
    skirental_ratio,
    worst_case_ratio,
)


def test_dwell_and_ratio():
    assert skirental_dwell(10) == 20.0
    assert skirental_ratio(10) == pytest.approx(1.95)
    assert skirental_ratio(5) == pytest.approx(2.0 - 1.0 / 10.0)


def test_minimax_is_two_lambda():
    lam = 10
    d_star, ratio = minimax_dwell(lam, candidates=[2, 5, 10, 15, 20, 25, 40, 80])
    assert d_star == skirental_dwell(lam) == 20
    assert ratio == pytest.approx(skirental_ratio(lam), abs=1e-6)
    # no other candidate dwell beats the 2*lambda worst-case ratio
    for d in (5, 10, 15, 25, 40, 80):
        assert worst_case_ratio(d, lam) >= ratio - 1e-9


def test_worst_case_ratio_at_dwell_star():
    for lam in (5, 10, 20):
        assert worst_case_ratio(2 * lam, lam) == pytest.approx(skirental_ratio(lam), abs=1e-6)


def test_closed_forms():
    lam = 10
    assert opt_slack_cost(8, lam) == 8        # short slack: hold through
    assert opt_slack_cost(40, lam) == 20      # long slack: buy at 2*lambda
    assert dwell_slack_cost(40, lam, 20) == (20 - 1) + 20   # d<=tau: rent d-1, then buy
    assert dwell_slack_cost(8, lam, 20) == 8               # d>tau: never releases
