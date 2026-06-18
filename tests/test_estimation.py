"""Tests for the estimation module — inferring quantities from traces.

Focus on the detection × fix-success decomposition: pre/post outcomes reveal
only the *effective* correction; the reviewer's flag log is needed to recover
the corrector's fix_rate.
"""

import pytest

from minimal_oversight.estimation import (
    estimate_catch_rate,
    estimate_fix_rate,
)


class TestEffectiveCorrection:
    def test_catch_rate_inverts_equation_6(self):
        # raw=0.6, corr=0.86 → c_eff = (0.86-0.6)/(1-0.6) = 0.65
        raw = [1, 1, 1, 0, 0]  # mean 0.6
        corr = [1, 1, 1, 1, 0]  # mean 0.8
        c_eff = estimate_catch_rate(raw, corr)
        expected = (0.8 - 0.6) / (1 - 0.6)
        assert pytest.approx(c_eff, rel=1e-9) == expected

    def test_none_when_no_errors(self):
        assert estimate_catch_rate([1, 1, 1], [1, 1, 1]) is None


class TestFixRate:
    def test_fix_rate_is_conditional_on_flagged(self):
        # 4 items flagged as errors; 3 repairs succeeded → f = 0.75.
        flagged = [1, 1, 1, 1, 0, 0]
        repaired = [1, 1, 1, 0, 0, 0]
        f = estimate_fix_rate(flagged, repaired)
        assert pytest.approx(f, rel=1e-9) == 0.75

    def test_unflagged_items_ignored(self):
        # A "success" on an unflagged item must not inflate fix_rate.
        flagged = [1, 0, 0, 0]
        repaired = [0, 1, 1, 1]
        assert estimate_fix_rate(flagged, repaired) == 0.0

    def test_none_when_nothing_flagged(self):
        assert estimate_fix_rate([0, 0, 0], [0, 0, 0]) is None
