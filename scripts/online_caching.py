#!/usr/bin/env python3
"""Where is the MULTI-AGENT coupling? Prove-or-break: shared oversight = caching.

The single-sink results (ski-rental + the sqrt(nu*sigma) noise floor) are the
already-published single-agent kernel. They do NOT make a multi-agent paper, and
here is precisely why: with delivered quality = min over sinks, feasibility is
PER-SINK (b_s >= r_s), so without coupling the k-sink problem SEPARATES into k
independent ski-rentals -- trivially k x the single-sink result. No coupling, no
multi-agent content.

The coupling is the literal meaning of *minimal* oversight: a FINITE shared review
capacity C the agents compete for. Let h = floor(C / b*) = how many bottleneck-level
sinks can be funded at once. Under drift the bottleneck moves between sinks, so the
controller must reallocate the scarce capacity -- keep budget on a recovered sink
(in case it returns) or release it to fund the new bottleneck. That is EXACTLY
ONLINE CACHING / PAGING:

    page in cache  <->  sink currently funded (holding b*)
    cache size h   <->  C / b*  (how many sinks fit in the oversight pool)
    page request   <->  a sink becomes the bottleneck (needs b*)
    cache miss     <->  a returning bottleneck was released -> re-fund it (pay 2 lambda b*)

Consequences we test (this script BREAKS the claim if the numbers disagree):
  C1  the monotone ratchet is INFEASIBLE under shared capacity once > h sinks have
      ever been a bottleneck (it would hold k*b* > C). Release is not better -- it
      is REQUIRED.
  C2  deterministic release (LRU eviction) is Theta(h)-competitive vs the offline
      optimum (Belady), and the cyclic adversary achieves it -- the classic paging
      lower bound. So the multi-agent competitive ratio is the cache size h.
  C3  randomised release (MARKER) is O(log h)-competitive -- the classic
      randomised-paging improvement, an exponential win the deterministic policy
      cannot get. (Genuinely multi-agent: it has no single-sink analogue.)
  C4  noisy bottleneck identity (you mis-see which sink is binding) degrades the
      ratio toward worst case -- composes the noise floor with the caching ratio.

Run:  python3 scripts/online_caching.py
"""

from __future__ import annotations

import numpy as np


# ------------------------- offline optimum (Belady) ------------------------ #
def belady_misses(requests, h):
    cache, misses = set(), 0
    for i, p in enumerate(requests):
        if p in cache:
            continue
        misses += 1
        if len(cache) < h:
            cache.add(p)
            continue
        # evict the cached page whose next use is farthest in the future
        def next_use(q):
            try:
                return requests[i + 1:].index(q)
            except ValueError:
                return len(requests)        # never used again
        victim = max(cache, key=next_use)
        cache.remove(victim)
        cache.add(p)
    return misses


# ----------------------------- online policies ----------------------------- #
def lru_misses(requests, h):
    cache, misses = [], 0
    for p in requests:
        if p in cache:
            cache.remove(p); cache.append(p)        # refresh recency
            continue
        misses += 1
        if len(cache) >= h:
            cache.pop(0)                            # evict least-recently-used
        cache.append(p)
    return misses


def marker_misses(requests, h, seed):
    rng = np.random.default_rng(seed)
    cache, marked, misses = set(), set(), 0
    for p in requests:
        if p in cache:
            marked.add(p)
            continue
        misses += 1
        if len(cache) >= h:
            unmarked = list(cache - marked)
            if not unmarked:                        # new phase: unmark all
                marked.clear()
                unmarked = list(cache)
            victim = unmarked[rng.integers(len(unmarked))]
            cache.remove(victim)
        cache.add(p); marked.add(p)
    return misses


def ratchet_capacity(requests):
    """Per-sink budget the never-release ratchet would hold = #distinct sinks seen
    (in units of b*). It must hold ALL sinks ever bottlenecked => needs capacity =
    that many. Returns the running max distinct count (the capacity it demands)."""
    seen = set()
    peak = 0
    for p in requests:
        seen.add(p)
        peak = max(peak, len(seen))
    return peak


# ------------------------------- instances --------------------------------- #
def cyclic(h, rounds):
    """The paging adversary: cycle through h+1 distinct sinks (cache holds h)."""
    pages = list(range(h + 1))
    return [pages[i % (h + 1)] for i in range(rounds * (h + 1))]


def zipf_requests(k, n, seed, s=1.1):
    rng = np.random.default_rng(seed)
    w = 1.0 / np.power(np.arange(1, k + 1), s)
    w /= w.sum()
    return list(rng.choice(k, size=n, p=w))


def add_noise(requests, k, p_confuse, seed):
    """With prob p_confuse, the controller mis-identifies the bottleneck as a random
    other sink (noisy argmin over sinks). Models bottleneck-identity uncertainty."""
    rng = np.random.default_rng(seed)
    out = []
    for p in requests:
        if rng.random() < p_confuse:
            out.append(int(rng.integers(k)))
        else:
            out.append(p)
    return out


# --------------------------------- tests ----------------------------------- #
def test_c1_ratchet_infeasible():
    print("C1 -- the monotone ratchet's demanded capacity grows to k*b* (infeasible "
          "under a finite pool):")
    print(f"  {'k sinks bottlenecked':>22s} {'ratchet needs (xb*)':>20s} "
          f"{'pool C=h*b*, h=4':>18s}")
    for k in (2, 4, 8, 16):
        req = cyclic(k - 1, 6) if k >= 2 else [0]
        need = ratchet_capacity(req)
        verdict = "OK" if need <= 4 else "INFEASIBLE (need > C)"
        print(f"  {k:22d} {need:20d} {verdict:>18s}")
    print("  -> once > h distinct sinks are ever the bottleneck, the ratchet "
          "cannot fit. Release is REQUIRED.\n")


def test_c2_lru_theta_h():
    print("C2 -- deterministic release (LRU) is Theta(h)-competitive vs Belady "
          "(cyclic adversary):")
    print(f"  {'h (cache=C/b*)':>15s} {'LRU miss':>9s} {'Belady miss':>12s} "
          f"{'CR':>7s}  (theory: CR -> h)")
    for h in (2, 3, 4, 6, 8):
        req = cyclic(h, 200)
        lm, bm = lru_misses(req, h), belady_misses(req, h)
        print(f"  {h:15d} {lm:9d} {bm:12d} {lm/bm:7.2f}")
    print("  -> CR tracks the cache size h: the multi-agent competitive ratio is "
          "the oversight pool size.\n")


def test_c3_marker_logh():
    print("C3 -- randomised release (MARKER) is O(log h): an exponential win over "
          "LRU's h (cyclic adversary, k=h+1):")
    print(f"  {'h':>4s} {'LRU CR (~h)':>12s} {'MARKER CR (~H_h)':>17s} "
          f"{'H_h=1+1/2+..+1/h':>17s}")
    for h in (4, 8, 16, 32):
        req = cyclic(h, 400)
        bm = belady_misses(req, h)
        lm = lru_misses(req, h)
        mk = np.mean([marker_misses(req, h, sd) for sd in range(8)])
        harmonic = float(np.sum(1.0 / np.arange(1, h + 1)))
        print(f"  {h:4d} {lm/bm:12.2f} {mk/bm:17.2f} {harmonic:17.2f}")
    print("  -> LRU's CR ~ h, MARKER's ~ H_h ~ ln h: randomisation is a genuine "
          "multi-agent lever with no single-sink analogue.\n")


def test_c4_noise_composes():
    print("C4 -- noisy bottleneck identity -> FORCED infeasibility under a tight pool")
    print("      (h slots, h+1 contenders: no spare slot to hedge a misidentification):")
    print(f"  {'p_confuse':>10s} {'infeasible rate':>16s} {'hedged (h+1 slots)':>19s}")
    h = 4
    req = cyclic(h, 400)
    for p in (0.0, 0.05, 0.15, 0.30):
        noisy = add_noise(req, h + 1, p, seed=3)
        rates = {}
        for slots in (h, h + 1):                     # tight pool vs one spare slot
            cache, infeas = [], 0
            for true_p, obs_p in zip(req, noisy):
                if obs_p in cache:
                    cache.remove(obs_p); cache.append(obs_p)
                else:
                    if len(cache) >= slots:
                        cache.pop(0)
                    cache.append(obs_p)
                if true_p not in cache:
                    infeas += 1
            rates[slots] = infeas / len(req) * 100
        print(f"  {p:10.2f} {rates[h]:15.1f}% {rates[h+1]:18.1f}%")
    print("  -> identity noise forces infeasibility precisely when the pool is tight;")
    print("     a spare slot lets the controller hedge. The clean composition with")
    print("     the noise floor (paging-with-noisy-predictions) is the open piece.\n")


def main() -> int:
    print("=" * 76)
    print("Multi-agent coupling: shared oversight capacity = ONLINE CACHING "
          "-- prove or break")
    print("=" * 76 + "\n")
    test_c1_ratchet_infeasible()
    test_c2_lru_theta_h()
    test_c3_marker_logh()
    test_c4_noise_composes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
