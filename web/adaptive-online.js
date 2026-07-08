/**
 * adaptive-online.js — browser port of the online review-control variants.
 *
 * Faithful re-implementation of the closed forms and online policies in
 *   src/minimal_oversight/skirental.py   (release = rent-or-buy / ski-rental)
 *   src/minimal_oversight/tracking.py    (drift under noise = Kalman + matched margin)
 *   src/minimal_oversight/caching.py     (finite shared review pool = online paging)
 * plus the full-instance ski-rental simulation in scripts/online_skirental.py
 * (requiredSeq / simulate / optCost / dwellCost / instanceCR).
 *
 * Every DETERMINISTIC function here is pinned to the Python reference by
 * tests/test_parity_online.py (|Δ| < 1e-6). MARKER eviction is randomized and uses
 * an in-file mulberry32 PRNG; it is NOT bit-identical to NumPy's generator — its
 * guarantee (CR ~ H_h, below LRU) is validated by bound, not by equality.
 *
 * Usage (browser):  <script src="../adaptive-online.js"></script>  then window.AdaptiveOnline
 * Usage (node):     const O = require('./adaptive-online.js')
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.AdaptiveOnline = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // ======================================================================== //
  // 1. Ski-rental — the release (rent-or-buy) decision.                       //
  //    Port of src/minimal_oversight/skirental.py (per-slack-phase forms)     //
  //    + scripts/online_skirental.py (full-instance simulation).             //
  // ======================================================================== //

  var BSTAR = 1.0; // peak required budget of the bottleneck when active

  // Optimal (minimax) release dwell: hold a slack node 2*lambda steps. (skirental.py)
  function skirentalDwell(lam) { return 2.0 * lam; }
  // Competitive ratio of the optimal dwell 2*lambda: 2 - 1/(2*lambda).
  function skirentalRatio(lam) { return 2.0 - 1.0 / (2.0 * lam); }
  // Clairvoyant cost over one slack phase of length tau: b*min(tau, 2*lambda).
  function optSlackCost(tau, lam, b) {
    b = b == null ? 1.0 : b;
    return b * Math.min(tau, 2.0 * lam);
  }
  // Cost of a fixed dwell-d policy over a slack phase of length tau.
  function dwellSlackCost(tau, lam, d, b) {
    b = b == null ? 1.0 : b;
    if (d <= tau) return b * ((d - 1) + 2.0 * lam);
    return b * tau;
  }
  // Worst-case competitive ratio of dwell d over slack lengths tau in [1, tauMax].
  function worstCaseRatio(d, lam, tauMax, b) {
    tauMax = tauMax == null ? 1000 : tauMax;
    var worst = 0.0;
    for (var tau = 1; tau <= tauMax; tau++) {
      worst = Math.max(worst, dwellSlackCost(tau, lam, d, b) / optSlackCost(tau, lam, b));
    }
    return worst;
  }
  // (dwell*, worstCaseRatio) minimizing the worst-case ratio over candidate dwells.
  function minimaxDwell(lam, candidates, tauMax) {
    tauMax = tauMax == null ? 1000 : tauMax;
    if (candidates == null) {
      var set = {};
      [1.0, lam, 1.5 * lam, 2.0 * lam, 2.5 * lam, 4.0 * lam].forEach(function (x) { set[x] = x; });
      candidates = Object.keys(set).map(Number).sort(function (a, b) { return a - b; });
    }
    var bestD = candidates[0], best = Infinity;
    for (var i = 0; i < candidates.length; i++) {
      var w = worstCaseRatio(candidates[i], lam, tauMax);
      if (w < best) { best = w; bestD = candidates[i]; }
    }
    return { dwell: bestD, ratio: best };
  }

  // ----- full-instance simulation (scripts/online_skirental.py) ------------ //
  // Single sink, recurring need: ncyc cycles of [active W][slack tau] + trailing active.
  function requiredSeq(W, tau, ncyc) {
    var cycle = [], i;
    for (i = 0; i < W; i++) cycle.push(BSTAR);
    for (i = 0; i < tau; i++) cycle.push(0.0);
    var seq = [];
    for (var c = 0; c < ncyc; c++) seq = seq.concat(cycle);
    for (i = 0; i < W; i++) seq.push(BSTAR);
    return seq;
  }
  // Offset to the next active step at-or-after t (Infinity if none). Mirrors next_need.
  function nextNeed(r, t) {
    for (var i = t; i < r.length; i++) if (r[i] > 0) return i - t;
    return Infinity;
  }
  // Simulate one policy on required-budget sequence r. Deterministic (no observation
  // noise — the showcase uses the noise-free cost geometry; tracking.py owns noise).
  // policy in {opt, ratchet, dwell}. Returns the per-step held budget b[], holding,
  // switching, infeasible-fraction. Mirrors scripts/online_skirental.py:run at sigma=0.
  function simulate(policy, r, lam, opts) {
    opts = opts || {};
    var dwell = opts.dwell == null ? 0 : opts.dwell;
    var margin = opts.margin == null ? 0.0 : opts.margin;
    var T = r.length, b = 0.0, streak = 0.0;
    var holding = 0.0, switching = 0.0, infeas = 0;
    var trace = new Array(T);
    for (var t = 0; t < T; t++) {
      var target = Math.max(r[t], 0.0) + margin;
      var prev = b;
      if (policy === "opt") {
        if (r[t] > 0) b = r[t];
        else b = nextNeed(r, t) < 2 * lam ? b : 0.0;
      } else if (policy === "ratchet") {
        b = Math.max(b, target);
      } else if (policy === "dwell") {
        if (target > b + 1e-12) { b = target; streak = 0; }
        else if (b > target + 1e-12) { streak += 1; if (streak >= dwell) b = target; }
        else streak = 0;
      } else throw new Error("unknown policy " + policy);
      holding += b;
      switching += Math.abs(b - prev);
      if (b < r[t] - 1e-9) infeas += 1;
      trace[t] = b;
    }
    return { trace: trace, holding: holding, switching: switching, infeas: infeas / T };
  }
  function instanceCost(holding, switching, lam) { return holding + lam * switching; }
  // Full-instance competitive ratio of a policy vs the clairvoyant optimum.
  function instanceCR(policy, W, tau, lam, ncyc, opts) {
    var r = requiredSeq(W, tau, ncyc);
    var p = simulate(policy, r, lam, opts);
    var o = simulate("opt", r, lam);
    return instanceCost(p.holding, p.switching, lam) / instanceCost(o.holding, o.switching, lam);
  }
  // Closed-form clairvoyant cost (scripts/online_skirental.py:opt_cost).
  function optCost(W, tau, lam, ncyc) {
    var activeHold = BSTAR * W * (ncyc + 1);
    if (tau >= 2 * lam) return activeHold + lam * (BSTAR + 2 * BSTAR * ncyc);
    return activeHold + BSTAR * tau * ncyc + lam * BSTAR;
  }
  // Closed-form fixed-dwell cost (scripts/online_skirental.py:dwell_cost).
  function dwellCost(W, tau, lam, ncyc, d) {
    var activeHold = BSTAR * W * (ncyc + 1), slackHold, sw;
    if (d <= tau) { slackHold = BSTAR * (d - 1) * ncyc; sw = BSTAR + 2 * BSTAR * ncyc; }
    else { slackHold = BSTAR * tau * ncyc; sw = BSTAR; }
    return activeHold + slackHold + lam * sw;
  }

  // ======================================================================== //
  // 2. Tracking under observation noise — the Kalman variant.                //
  //    Port of src/minimal_oversight/tracking.py.                            //
  // ======================================================================== //

  var Z_DELTA_98 = 2.054; // one-sided Phi^{-1}(0.98); target infeasibility 2%

  // Steady-state posterior variance P* (positive Riccati root) for random-walk
  // drift nu and observation noise sigma.
  function kalmanSteadystateVar(nu, sigma) {
    var q = nu * nu, r = sigma * sigma;
    return (-q + Math.sqrt(q * q + 4.0 * q * r)) / 2.0;
  }
  // Feasibility margin z_delta * sqrt(pStar).
  function matchedMargin(pStar, zDelta) {
    zDelta = zDelta == null ? Z_DELTA_98 : zDelta;
    return zDelta * Math.sqrt(pStar);
  }
  // Per-step holding-regret floor z_delta * sqrt(P*) (Kalman-matched).
  function noiseFloorPerStep(nu, sigma, zDelta) {
    zDelta = zDelta == null ? Z_DELTA_98 : zDelta;
    return matchedMargin(kalmanSteadystateVar(nu, sigma), zDelta);
  }
  // Unfiltered deadband margin z_delta * sigma (a factor sqrt(sigma/nu) above floor).
  function deadbandMargin(sigma, zDelta) {
    zDelta = zDelta == null ? Z_DELTA_98 : zDelta;
    return zDelta * sigma;
  }

  // Causal scalar Kalman filter; stateful, one observation per control step.
  function KalmanTracker(nu, sigma, xhat, varInit) {
    this.nu = nu;
    this.sigma = sigma;
    this.xhat = xhat == null ? 0.0 : xhat;
    this.var = varInit == null ? sigma * sigma : varInit;
  }
  KalmanTracker.prototype.update = function (obs) {
    var q = this.nu * this.nu, r = this.sigma * this.sigma;
    var varPred = this.var + q;
    var gain = varPred / (varPred + r);
    this.xhat = this.xhat + gain * (obs - this.xhat);
    this.var = (1.0 - gain) * varPred;
    return this.xhat;
  };
  KalmanTracker.prototype.feasibleBudget = function (obs, zDelta) {
    zDelta = zDelta == null ? Z_DELTA_98 : zDelta;
    var est = this.update(obs);
    return est + zDelta * Math.sqrt(this.var);
  };

  // ======================================================================== //
  // 3. Shared finite review pool — the online-paging variant.                //
  //    Port of src/minimal_oversight/caching.py.                             //
  // ======================================================================== //

  // Deterministic seeded PRNG (mulberry32) for MARKER. NOT NumPy-compatible.
  function mulberry32(seed) {
    var a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Number of bottleneck-level sinks that fit in a review pool of size c: floor(c/b*).
  function poolCapacity(c, bStar) {
    if (bStar <= 0) throw new Error("b_star must be positive");
    return Math.floor(c / bStar);
  }
  // Offline optimum (Belady): evict the funded sink whose next request is farthest.
  function beladyMisses(requests, h) {
    var cache = [], misses = 0;
    for (var i = 0; i < requests.length; i++) {
      var p = requests[i];
      if (cache.indexOf(p) !== -1) continue;
      misses++;
      if (cache.length < h) { cache.push(p); continue; }
      var future = requests.slice(i + 1);
      var evict = cache[0], best = -1;
      for (var c = 0; c < cache.length; c++) {
        var idx = future.indexOf(cache[c]);
        var nu = idx === -1 ? future.length + 1 : idx;
        if (nu > best) { best = nu; evict = cache[c]; }
      }
      cache.splice(cache.indexOf(evict), 1);
      cache.push(p);
    }
    return misses;
  }
  // Deterministic least-recently-used eviction. Theta(h)-competitive.
  function lruMisses(requests, h) {
    var cache = [], misses = 0;
    for (var i = 0; i < requests.length; i++) {
      var p = requests[i], at = cache.indexOf(p);
      if (at !== -1) { cache.splice(at, 1); cache.push(p); continue; }
      misses++;
      if (cache.length >= h) cache.shift();
      cache.push(p);
    }
    return misses;
  }
  // Randomized MARKER eviction (a random unmarked page). O(log h)-competitive.
  function markerMisses(requests, h, seed) {
    var rng = mulberry32(seed == null ? 0 : seed);
    var cache = {}, marked = {}, size = 0, misses = 0;
    for (var i = 0; i < requests.length; i++) {
      var p = requests[i];
      if (cache[p]) { marked[p] = true; continue; }
      misses++;
      if (size >= h) {
        var unmarked = [];
        for (var k in cache) if (cache[k] && !marked[k]) unmarked.push(k);
        if (!unmarked.length) {
          marked = {};
          for (var k2 in cache) if (cache[k2]) unmarked.push(k2);
        }
        var victim = unmarked[Math.floor(rng() * unmarked.length)];
        delete cache[victim]; delete marked[victim]; size--;
      }
      cache[p] = true; marked[p] = true; size++;
    }
    return misses;
  }
  // Capacity (in units of b*) the never-release ratchet demands: distinct sink count.
  function ratchetDemand(requests) {
    var set = {}, n = 0;
    for (var i = 0; i < requests.length; i++) if (!set[requests[i]]) { set[requests[i]] = true; n++; }
    return n;
  }
  // Competitive ratio of an online eviction policy ('lru'|'marker') vs Belady.
  function competitiveRatio(policy, requests, h, seed) {
    var on;
    if (policy === "lru") on = lruMisses(requests, h);
    else if (policy === "marker") on = markerMisses(requests, h, seed);
    else throw new Error("unknown policy " + policy);
    var off = beladyMisses(requests, h);
    return off ? on / off : Infinity;
  }
  // The paging lower-bound instance: cycle h+1 distinct sinks through a pool of h.
  function cyclicAdversary(h, rounds) {
    var pages = [], i;
    for (i = 0; i <= h; i++) pages.push(i);
    var out = [];
    for (i = 0; i < rounds * (h + 1); i++) out.push(pages[i % (h + 1)]);
    return out;
  }

  // Adaptive review controller under a finite shared review pool of size h. Drive one
  // bottleneck at a time via request(sink). Mirrors lruMisses/markerMisses exactly.
  function SharedPoolController(h, policy, seed) {
    policy = policy == null ? "lru" : policy;
    if (policy !== "lru" && policy !== "marker") throw new Error("unknown policy " + policy);
    this.h = h;
    this.policy = policy;
    this.funded = [];
    this.marked = {};
    this.misses = 0;
    this._rng = mulberry32(seed == null ? 0 : seed);
  }
  SharedPoolController.prototype.request = function (sink) {
    var at = this.funded.indexOf(sink);
    if (at !== -1) {
      if (this.policy === "lru") { this.funded.splice(at, 1); this.funded.push(sink); }
      else this.marked[sink] = true;
      return false;
    }
    this.misses++;
    if (this.funded.length >= this.h) this._evict();
    this.funded.push(sink);
    if (this.policy === "marker") this.marked[sink] = true;
    return true;
  };
  SharedPoolController.prototype._evict = function () {
    if (this.policy === "lru") { this.funded.shift(); return; }
    var unmarked = this.funded.filter(function (s) { return !this.marked[s]; }, this);
    if (!unmarked.length) { this.marked = {}; unmarked = this.funded.slice(); }
    var victim = unmarked[Math.floor(this._rng() * unmarked.length)];
    this.funded.splice(this.funded.indexOf(victim), 1);
    delete this.marked[victim];
  };

  return {
    version: "0.1.0",
    // ski-rental (per-phase)
    skirentalDwell: skirentalDwell, skirentalRatio: skirentalRatio,
    optSlackCost: optSlackCost, dwellSlackCost: dwellSlackCost,
    worstCaseRatio: worstCaseRatio, minimaxDwell: minimaxDwell,
    // ski-rental (full instance)
    BSTAR: BSTAR, requiredSeq: requiredSeq, nextNeed: nextNeed, simulate: simulate,
    instanceCost: instanceCost, instanceCR: instanceCR, optCost: optCost, dwellCost: dwellCost,
    // tracking
    Z_DELTA_98: Z_DELTA_98, kalmanSteadystateVar: kalmanSteadystateVar,
    matchedMargin: matchedMargin, noiseFloorPerStep: noiseFloorPerStep,
    deadbandMargin: deadbandMargin, KalmanTracker: KalmanTracker,
    // caching
    poolCapacity: poolCapacity, beladyMisses: beladyMisses, lruMisses: lruMisses,
    markerMisses: markerMisses, ratchetDemand: ratchetDemand,
    competitiveRatio: competitiveRatio, cyclicAdversary: cyclicAdversary,
    SharedPoolController: SharedPoolController, mulberry32: mulberry32
  };
});
