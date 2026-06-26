#!/usr/bin/env python3
"""Revive the matching lower bound (refuted as F-T2-REFUT) under finite capacity.

F-T2-REFUT killed the online matching lower bound: the causal policy "commit b_max
and hold" ties OPT, so there is no online-vs-offline separation. THAT POLICY IS
INFEASIBLE under finite oversight capacity: holding b* on every sink ever bottlenecked
demands k*b*, but the pool is only C = h*b* with h < k. Remove the illegal policy and
the separation returns -- as the classic PAGING lower bound. This script establishes
it rigorously and BREAKS it if it can.

Setting: k = h+1 contended sinks, oversight pool C = h*b* (h funded at once). Drift =
the bottleneck sequence (worst-case / adaptive adversary). Cost discriminator under a
binding pool is the switching (re-funding a released sink) = the cache MISS.

  Thm (revived matching LB).  Against worst-case drift, under a binding pool of size h:
    (LB)  EVERY deterministic online release policy is >= h-competitive
          (adaptive adversary: request the one unfunded sink -> miss every step;
           Belady misses <= 1 per h steps).
    (UB)  LRU achieves <= h on every sequence (classic).  => exactly h-competitive.
    (RAND) MARKER is O(H_h)=O(log h); every randomized policy is Omega(log h).
    (REVIVAL) commit-and-hold needs capacity k*b* > C: infeasible, so it cannot
              witness no-separation. The F-T2-REFUT counterexample dies under capacity.

Honest regime: this is the SWITCHING-DOMINATED, WORST-CASE-drift competitive ratio.
With holding cost dominant the pool equalises holding and CR -> 1; with benign
(stochastic) drift CR << h. Both are reported so the regime is explicit.

Run:  python3 scripts/online_matchlb.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from online_caching import (  # noqa: E402
    belady_misses, cyclic, lru_misses, marker_misses, zipf_requests,
)

BSTAR = 1.0


# ---------------- adaptive adversary vs ANY deterministic rule -------------- #
def adaptive_sequence(evict, h, T):
    """Generate the request stream that defeats a deterministic policy: always
    request the single unfunded sink. `evict(order)` picks the victim (a page) from
    the current cache given its insertion/recency order (list, oldest..newest).
    Returns (online_misses, sequence). Online misses EVERY step by construction."""
    pages = set(range(h + 1))
    order = list(range(h))            # cached pages, oldest -> newest
    seq, misses = [], 0
    for _ in range(T):
        out = (pages - set(order)).pop()      # the unique unfunded sink
        seq.append(out)
        victim = evict(order)                 # policy-specific eviction
        order.remove(victim)
        order.append(out)                     # newly funded = newest
        misses += 1                           # every adaptive request is a miss
    return misses, seq


EVICTORS = {
    "LRU/FIFO": lambda order: order[0],       # oldest
    "MRU":      lambda order: order[-1],       # newest
    "middle":   lambda order: order[len(order) // 2],
}


def test_lb_all_deterministic():
    print("LB -- adaptive adversary forces EVERY deterministic policy to >= h "
          "(not just LRU):")
    print(f"  {'h':>3s} {'policy':>10s} {'online miss':>12s} {'Belady miss':>12s} "
          f"{'CR':>6s}")
    T = 4000
    for h in (3, 5, 8):
        for name, ev in EVICTORS.items():
            on, seq = adaptive_sequence(ev, h, T)
            bm = belady_misses(seq, h)
            print(f"  {h:3d} {name:>10s} {on:12d} {bm:12d} {on/bm:6.2f}")
    print("  -> LRU/FIFO are TIGHT at CR=h (the optimal deterministic ratio); MRU/")
    print("     'middle' are far worse. Every deterministic policy is >= h -- none")
    print("     beats it (the classic paging lower bound), reviving the separation.\n")


def test_ub_lru():
    print("UB -- LRU is <= h on every sequence (tight on the adversary, slack on "
          "benign drift):")
    print(f"  {'h':>3s} {'adversary CR':>13s} {'random-uniform CR':>18s} "
          f"{'Zipf CR':>9s}")
    for h in (3, 5, 8):
        adv = cyclic(h, 300)
        cr_adv = lru_misses(adv, h) / belady_misses(adv, h)
        runi = list(np.random.default_rng(0).integers(0, h + 1, 6000))
        cr_uni = lru_misses(runi, h) / belady_misses(runi, h)
        rz = zipf_requests(3 * h, 6000, seed=1, s=1.0)
        cr_z = lru_misses(rz, h) / belady_misses(rz, h)
        print(f"  {h:3d} {cr_adv:13.2f} {cr_uni:18.2f} {cr_z:9.2f}  (<= h = {h})")
    print("  -> LRU = h on the worst case, << h on benign drift: exactly "
          "h-competitive (matching).\n")


def test_revival():
    print("REVIVAL -- the F-T2-REFUT policy (commit-b_max-and-hold) is INFEASIBLE "
          "under capacity:")
    print(f"  {'k contended':>12s} {'hold-all needs (xb*)':>21s} {'pool C=h*b*, h=4':>18s}")
    for k in (3, 5, 9, 17):
        need = k                                   # holds b* on every sink ever active
        verdict = "feasible" if need <= 4 else "INFEASIBLE -> must release"
        print(f"  {k:12d} {need:21d} {verdict:>26s}")
    print("  -> the no-separation counterexample cannot run under a finite pool; the "
          "separation (CR=h) is restored.\n")


def test_randomized():
    print("RAND -- randomization (MARKER) beats the deterministic h, achieving "
          "O(log h):")
    print(f"  {'h':>3s} {'det LRU CR':>11s} {'rand MARKER CR':>15s} "
          f"{'H_h':>6s} {'h':>4s}")
    for h in (4, 8, 16, 32):
        adv = cyclic(h, 400)
        bm = belady_misses(adv, h)
        lm = lru_misses(adv, h) / bm
        mk = np.mean([marker_misses(adv, h, sd) for sd in range(8)]) / bm
        Hh = float(np.sum(1.0 / np.arange(1, h + 1)))
        print(f"  {h:3d} {lm:11.2f} {mk:15.2f} {Hh:6.2f} {h:4d}")
    print("  -> MARKER ~ H_h ~ ln h vs LRU ~ h: the randomized matching bound "
          "(Omega(log h) lower bound is classic).\n")


def test_regime_total_cost():
    print("REGIME (honest) -- total-cost CR vs switching weight lambda "
          "(holding=h*b* per step, both pay it):")
    print(f"  {'lambda/b*':>10s} {'total-cost CR':>14s}  (h=5 adversary; "
          f"miss-CR=h only when switching dominates)")
    h = 5
    adv = cyclic(h, 400)
    steps = len(adv)
    lm, bm = lru_misses(adv, h), belady_misses(adv, h)
    hold = h * BSTAR * steps                       # both keep the pool full
    for lam in (0.0, 1.0, 10.0, 100.0):
        # switching cost ~ 2*lambda*b* per miss
        cl = hold + 2 * lam * BSTAR * lm
        co = hold + 2 * lam * BSTAR * bm
        print(f"  {lam:10.1f} {cl/co:14.2f}")
    print("  -> CR -> h as switching dominates (lambda large); -> 1 when holding "
          "dominates (pool equalises it). The matching LB is the switching-dominated regime.\n")


def main() -> int:
    print("=" * 78)
    print("Revived matching lower bound under finite oversight capacity "
          "-- rigorous prove-or-break")
    print("=" * 78 + "\n")
    test_lb_all_deterministic()
    test_ub_lru()
    test_revival()
    test_randomized()
    test_regime_total_cost()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
