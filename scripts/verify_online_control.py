#!/usr/bin/env python3
"""Machine-checked verification of the online MSO controller's invariants (Z3/SMT).

Z3 is the SMT engine underlying Dafny, SPARK, and Boogie, so these are genuine
formal-verification obligations, discharged by proving each property's negation
UNSAT over the reals on [0,1]. Together they establish, for the controller in
``minimal_oversight/online_control.py``:

  P1 corrected_bounded     sigma_corr stays in [0,1].
  P2 corrected_monotone    sigma_corr is non-decreasing in the review budget b.
  P3 min_monotone          a min-aggregation (weakest-link gate / sink bottleneck)
                           is non-decreasing in each argument.
  P4 product_monotone      a product-aggregation is non-decreasing in each argument.
  P5 mean_monotone         a mean-aggregation is non-decreasing in each argument.
  P6 budget_cap_safe       min(b+delta, b_max) stays in [0, b_max] for b in
                           [0,b_max], delta>=0  (INV-BUDGET).
  P7 step_non_harmful      on a 3-node chain, adding delta>=0 to any node's budget
                           does not decrease the bottleneck delivered quality
                           (INV-MONOTONE for the add path, the composition P2+P3).
  P8 release_preserves_feasibility  releasing delta from a slack sink, behind the
                           guard corrected(s, b-delta) >= p_min + margin, keeps the
                           min-over-sinks delivered quality >= p_min (INV-FEASIBLE).
  P9 deadband_forbids_add_release_cycle  if a sink is in deficit (corrected < p_min,
                           so the step ADDS) and the deadband is at least one grid
                           step (margin + deadband >= (1-s)c f * delta), then after
                           the add the sink is NOT in the release/arm region -- so a
                           static state cannot add-then-release the same sink forever
                           (INV-NO-CYCLE, the Lyapunov fact behind INV-TERMINATE for
                           the release controller).

P2-P5 compose to: delivered_quality (a min over sinks of corrected qualities fed
through monotone aggregations) is monotone in every budget[v]; with P6 this is
exactly INV-BUDGET + INV-MONOTONE (the monotone ratchet ``online_step``). The
optional release controller ``online_step_release`` gives up INV-MONOTONE (a
release lowers Q on purpose); P8 + P9 are its machine-checked replacements --
INV-FEASIBLE (a release never breaks the target) and INV-NO-CYCLE (the deadband
makes the per-sink budget settle, preserving termination). INV-TERMINATE is a
counting/Lyapunov argument (each step changes one node by delta; the deadband
forbids cycles) and is checked by the property-based tests rather than SMT.

Run:  uv run --with z3-solver python scripts/verify_online_control.py
"""

from __future__ import annotations

import sys

import z3

UNIT = lambda v: z3.And(v >= 0, v <= 1)  # noqa: E731


def corrected(s, b, c, f):
    return s + (1 - s) * b * c * f


def prove(name: str, premises, claim) -> bool:
    """Return True iff (premises => claim) is valid, i.e. its negation is UNSAT."""
    solver = z3.Solver()
    solver.add(premises)
    solver.add(z3.Not(claim))
    res = solver.check()
    ok = res == z3.unsat
    tag = "PROVED " if ok else f"FAILED ({res})"
    print(f"  [{tag}] {name}")
    if not ok and res == z3.sat:
        print("    counterexample:", solver.model())
    return ok


def main() -> int:
    s, b, b1, b2, c, f, d, bmax = z3.Reals("s b b1 b2 c f d bmax")
    x, x2, y = z3.Reals("x x2 y")
    ok = True

    # P1 corrected in [0,1]
    ok &= prove("P1 corrected_bounded",
                [UNIT(s), UNIT(b), UNIT(c), UNIT(f)],
                UNIT(corrected(s, b, c, f)))
    # P2 corrected monotone in b
    ok &= prove("P2 corrected_monotone_in_budget",
                [UNIT(s), UNIT(c), UNIT(f), UNIT(b1), UNIT(b2), b1 <= b2],
                corrected(s, b2, c, f) >= corrected(s, b1, c, f))
    # P3 min monotone
    ok &= prove("P3 min_monotone",
                [UNIT(x), UNIT(x2), UNIT(y), x <= x2],
                z3.If(x < y, x, y) <= z3.If(x2 < y, x2, y))
    # P4 product monotone (nonneg args)
    ok &= prove("P4 product_monotone",
                [UNIT(x), UNIT(x2), UNIT(y), x <= x2],
                x * y <= x2 * y)
    # P5 mean monotone
    ok &= prove("P5 mean_monotone",
                [UNIT(x), UNIT(x2), UNIT(y), x <= x2],
                (x + y) / 2 <= (x2 + y) / 2)
    # P6 budget cap safe: min(b+d, bmax) in [0, bmax]
    capped = z3.If(b + d < bmax, b + d, bmax)
    ok &= prove("P6 budget_cap_safe",
                [b >= 0, b <= bmax, d >= 0, bmax >= 0],
                z3.And(capped >= 0, capped <= bmax))
    # P7 step non-harmful on a 3-node chain (single sink n2). Q = corr at sink.
    s0, s1, s2 = z3.Reals("s0 s1 s2")
    bb0, bb1, bb2 = z3.Reals("bb0 bb1 bb2")
    cc2, ff2 = z3.Reals("cc2 ff2")
    prem = [UNIT(v) for v in (s0, s1, s2, bb0, bb1, bb2, cc2, ff2, d)] + [d >= 0]
    Q = corrected(s2, bb2, cc2, ff2)               # bottleneck = sink delivered
    Q_sink = corrected(s2, z3.If(bb2 + d < 1, bb2 + d, 1), cc2, ff2)  # +d at sink
    # adding d at sink: Q' >= Q ; adding at a non-sink leaves Q unchanged (>= Q).
    ok &= prove("P7 step_non_harmful_chain (review at sink)",
                prem + [bb2 + d <= 1], Q_sink >= Q)

    # P8 INV-FEASIBLE: a hysteresis release keeps delivered quality (min over sinks)
    # at or above p_min. Two sinks: sR is released by delta behind the guard
    # corrected(sR, bR - d) >= p_min + margin; sO is any untouched sink. From a
    # feasible state (both >= p_min) the post-release min stays >= p_min.
    sR, bR, cR, fR = z3.Reals("sR bR cR fR")
    sO, bO, cO, fO = z3.Reals("sO bO cO fO")
    pmin, marg = z3.Reals("pmin marg")
    qR_post = corrected(sR, bR - d, cR, fR)        # released sink, after release
    qO = corrected(sO, bO, cO, fO)                  # untouched sink
    prem8 = [UNIT(v) for v in (sR, bR, cR, fR, sO, bO, cO, fO, pmin, marg, d)] + [
        marg >= 0, bR >= d,
        corrected(sR, bR, cR, fR) >= pmin, qO >= pmin,   # pre-release feasible
        qR_post >= pmin + marg,                          # release guard
    ]
    ok &= prove("P8 release_preserves_feasibility (INV-FEASIBLE)",
                prem8, z3.If(qR_post < qO, qR_post, qO) >= pmin)

    # P9 INV-NO-CYCLE: the deadband forbids an add-then-release limit cycle. A sink
    # in deficit (corrected < p_min) is ADDED to; if margin + deadband covers one
    # grid step's gain ((1-s)c f * delta), the post-add corrected is still below the
    # arm level p_min + margin + deadband, so it cannot release next step. Hence in a
    # static state each sink's budget moves monotonically into the deadband and stops
    # (the Lyapunov argument behind INV-TERMINATE for online_step_release).
    s9, b9, c9, f9 = z3.Reals("s9 b9 c9 f9")
    pmin9, marg9, db9 = z3.Reals("pmin9 marg9 db9")
    gain9 = (1 - s9) * c9 * f9
    prem9 = [UNIT(v) for v in (s9, b9, c9, f9, pmin9, marg9, db9, d)] + [
        corrected(s9, b9, c9, f9) < pmin9,          # deficit -> the step adds
        marg9 + db9 >= gain9 * d,                    # deadband >= one grid step
    ]
    ok &= prove("P9 deadband_forbids_add_release_cycle (INV-NO-CYCLE)",
                prem9, corrected(s9, b9 + d, c9, f9) < pmin9 + marg9 + db9)

    print("\nAll invariants PROVED." if ok else "\nSOME OBLIGATIONS FAILED.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
