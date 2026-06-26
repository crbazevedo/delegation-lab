"""Shared finite review capacity: the online-paging variant of release.

With delivered quality the minimum over sinks, feasibility is per-sink, so without
coupling the ``k``-sink problem separates into ``k`` independent ski-rentals. The
coupling that makes it genuinely multi-sink is a *finite shared review pool* of
capacity ``C``: at most ``h = floor(C / b*)`` sinks can be funded at the bottleneck
level at once. Under drift the bottleneck moves, so the controller must EVICT a funded
sink to fund a new one -- exactly online paging, with "re-fund a released sink" as a
cache miss (cost ``2 * lambda * b*``).

Consequences (validated by ``scripts/online_caching.py`` /
``scripts/online_matchlb.py``):

* the never-release ratchet is INFEASIBLE once more than ``h`` distinct sinks have
  been the bottleneck -- it would hold ``> C`` (see :func:`ratchet_demand`);
* deterministic eviction (LRU) is ``Theta(h)``-competitive vs the offline optimum
  (Belady), tight on the cyclic adversary;
* randomized eviction (MARKER) is ``O(log h)``-competitive -- an exponential
  improvement available only because there are several sinks to randomize over.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def pool_capacity(c: float, b_star: float) -> int:
    """Number of bottleneck-level sinks that fit in a review pool of size ``c``:
    ``h = floor(c / b*)``."""
    if b_star <= 0:
        raise ValueError("b_star must be positive")
    return int(c // b_star)


# --------------------------------------------------------------------------- #
# Eviction policies (miss counts on a request sequence of sink ids).          #
# --------------------------------------------------------------------------- #
def belady_misses(requests: Sequence, h: int) -> int:
    """Offline optimum (Belady): evict the funded sink whose next request is farthest
    in the future. The competitive yardstick for the online policies."""
    cache: set = set()
    misses = 0
    for i, p in enumerate(requests):
        if p in cache:
            continue
        misses += 1
        if len(cache) < h:
            cache.add(p)
            continue
        future = requests[i + 1:]

        def next_use(q):
            try:
                return future.index(q)
            except ValueError:
                return len(future) + 1

        cache.remove(max(cache, key=next_use))
        cache.add(p)
    return misses


def lru_misses(requests: Sequence, h: int) -> int:
    """Deterministic least-recently-used eviction. ``Theta(h)``-competitive."""
    cache: list = []
    misses = 0
    for p in requests:
        if p in cache:
            cache.remove(p)
            cache.append(p)
            continue
        misses += 1
        if len(cache) >= h:
            cache.pop(0)
        cache.append(p)
    return misses


def marker_misses(requests: Sequence, h: int, seed: int = 0) -> int:
    """Randomized MARKER eviction (a random unmarked page). ``O(log h)``-competitive."""
    rng = np.random.default_rng(seed)
    cache: set = set()
    marked: set = set()
    misses = 0
    for p in requests:
        if p in cache:
            marked.add(p)
            continue
        misses += 1
        if len(cache) >= h:
            unmarked = list(cache - marked)
            if not unmarked:
                marked.clear()
                unmarked = list(cache)
            cache.remove(unmarked[rng.integers(len(unmarked))])
        cache.add(p)
        marked.add(p)
    return misses


def ratchet_demand(requests: Sequence) -> int:
    """Capacity (in units of ``b*``) the never-release ratchet would demand: the number
    of distinct sinks ever requested. Infeasible whenever this exceeds ``h``."""
    return len(set(requests))


def competitive_ratio(policy: str, requests: Sequence, h: int, seed: int = 0) -> float:
    """Competitive ratio of an online eviction ``policy`` ('lru' | 'marker') vs Belady."""
    if policy == "lru":
        on = lru_misses(requests, h)
    elif policy == "marker":
        on = marker_misses(requests, h, seed)
    else:
        raise ValueError(f"unknown policy {policy!r}")
    off = belady_misses(requests, h)
    return on / off if off else float("inf")


def cyclic_adversary(h: int, rounds: int) -> list[int]:
    """The paging lower-bound instance: cycle through ``h + 1`` distinct sinks while the
    pool holds only ``h`` -- forces ``Theta(h)`` for any deterministic policy."""
    pages = list(range(h + 1))
    return [pages[i % (h + 1)] for i in range(rounds * (h + 1))]


class SharedPoolController:
    """Online MSO controller under a finite shared review pool of size ``h``.

    Drive it one bottleneck at a time: :meth:`request` takes the id of the sink that is
    currently the bottleneck and (re)funds it, evicting a funded sink by ``policy``
    ('lru' | 'marker') when the pool is full. ``misses`` counts re-fund (switching)
    events. Mirrors :func:`lru_misses` / :func:`marker_misses` exactly.
    """

    def __init__(self, h: int, policy: str = "lru", seed: int = 0) -> None:
        if policy not in ("lru", "marker"):
            raise ValueError(f"unknown policy {policy!r}")
        self.h = h
        self.policy = policy
        self.funded: list = []
        self.marked: set = set()
        self.misses = 0
        self._rng = np.random.default_rng(seed)

    def request(self, sink) -> bool:
        """Bottleneck is ``sink``. Returns ``True`` on a miss (had to (re)fund it)."""
        if sink in self.funded:
            if self.policy == "lru":
                self.funded.remove(sink)
                self.funded.append(sink)
            else:
                self.marked.add(sink)
            return False
        self.misses += 1
        if len(self.funded) >= self.h:
            self._evict()
        self.funded.append(sink)
        if self.policy == "marker":
            self.marked.add(sink)
        return True

    def _evict(self) -> None:
        if self.policy == "lru":
            self.funded.pop(0)
        else:
            unmarked = [s for s in self.funded if s not in self.marked]
            if not unmarked:
                self.marked.clear()
                unmarked = list(self.funded)
            self.funded.remove(unmarked[self._rng.integers(len(unmarked))])
