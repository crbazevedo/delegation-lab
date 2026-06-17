/**
 * mso-sim.js — stochastic token simulation of a delegated pipeline.
 *
 * A lightweight Stochastic-Petri-Net-style simulator: tasks are tokens, nodes
 * are transitions that fire stochastically (raw success ~ Bernoulli(skill_eff),
 * review ~ Bernoulli(K/N), correction ~ Bernoulli(c)), and a review loop is a
 * real back-arc — a failed-and-uncaught token returns to the node up to k times.
 *
 * Semantics mirror `minimal_oversight.simulation.generate_synthetic_traces`
 * (hard 0/1 propagation: a node's effective skill is its own skill times the
 * AGGREGATE of its parents' corrected 0/1 outcomes). This is a DISCRETE level of
 * the model; the closed-form MSO (mso-core.js) is the mean-field level. They
 * agree to within a few percent — validated by tests/test_sim_grounding.py, not
 * by bit-parity (RNG differs across languages).
 *
 * Depends on mso-core.js for topo order + effectiveSkill.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./mso-core.js"));
  else root.MSOSim = factory(root.MSO);
})(typeof self !== "undefined" ? self : this, function (MSO) {
  "use strict";

  // Deterministic seedable PRNG (mulberry32) so runs are reproducible.
  function makeRng(seed) {
    var s = (seed >>> 0) || 1;
    return function () {
      s |= 0; s = (s + 0x6d2b79f5) | 0;
      var t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function agg(vals, type) {
    if (!vals.length) return 1;
    if (type === "min" || type === "weakest_link") return Math.min.apply(null, vals);
    if (type === "mean" || type === "weighted_mean") return vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
    return vals.reduce(function (a, b) { return a * b; }, 1);
  }

  // Run one task (token) through the pipeline; returns per-node {raw, corrected, loops}.
  function sampleTask(pipeline, opts, rng) {
    opts = opts || {};
    var byId = {}; pipeline.nodes.forEach(function (n) { byId[n.id] = n; });
    var order = MSO.topoOrder(pipeline.nodes);
    var eta = opts.eta == null ? 10 : opts.eta, delta = opts.delta == null ? 2 : opts.delta, s0 = opts.sigma_0 == null ? 0 : opts.sigma_0;
    var rec = {};
    order.forEach(function (id) {
      var n = byId[id];
      var skill = n.sigma_skill == null ? 0.55 : n.sigma_skill;
      var c = n.catch_rate == null ? 0.65 : n.catch_rate;
      var kn = n.review_capacity == null ? 1.0 : n.review_capacity;
      var rework = n.rework || 1;
      var parents = n.parents || [];
      var skillEff = parents.length
        ? skill * agg(parents.map(function (p) { return rec[p] ? rec[p].corrected : 1; }), n.aggregation || "product")
        : skill;
      // σ_raw fixed point as the per-task success probability (mean-field competence)
      var sraw = MSO.sigmaRawFixedPoint(skillEff, eta, delta, s0);
      var loops = 0, raw = rng() < sraw ? 1 : 0, corrected = raw;
      // review + rework loop: retry up to `rework` passes while uncaught failure
      for (var pass = 0; pass < rework && corrected === 0; pass++) {
        var reviewed = rng() < kn;
        if (reviewed && rng() < c) { corrected = 1; }
        else if (pass + 1 < rework) { loops++; raw = rng() < sraw ? 1 : 0; if (raw === 1) corrected = 1; }
      }
      rec[id] = { raw: raw, corrected: corrected, loops: loops };
    });
    return { order: order, rec: rec };
  }

  // Run n tasks; aggregate empirical end-to-end success + per-node raw/corrected/masking.
  function simulateTokens(pipeline, opts) {
    opts = opts || {};
    var n = opts.n == null ? 5000 : opts.n;
    var rng = opts.rng || makeRng(opts.seed == null ? 1 : opts.seed);
    var sinks = pipeline.nodes.filter(function (nd) {
      return !pipeline.nodes.some(function (m) { return (m.parents || []).indexOf(nd.id) >= 0; });
    }).map(function (nd) { return nd.id; });
    var sumRaw = {}, sumCorr = {}, loops = {};
    pipeline.nodes.forEach(function (nd) { sumRaw[nd.id] = 0; sumCorr[nd.id] = 0; loops[nd.id] = 0; });
    var endSuccess = 0;
    for (var i = 0; i < n; i++) {
      var t = sampleTask(pipeline, opts, rng);
      pipeline.nodes.forEach(function (nd) {
        var r = t.rec[nd.id]; if (!r) return;
        sumRaw[nd.id] += r.raw; sumCorr[nd.id] += r.corrected; loops[nd.id] += r.loops;
      });
      var ok = sinks.every(function (s) { return t.rec[s] && t.rec[s].corrected === 1; });
      if (ok) endSuccess++;
    }
    var perNode = {};
    pipeline.nodes.forEach(function (nd) {
      var raw = sumRaw[nd.id] / n, corr = sumCorr[nd.id] / n;
      perNode[nd.id] = { raw: raw, corrected: corr, masking: raw > 0 ? corr / raw : 1, avg_loops: loops[nd.id] / n };
    });
    return { n: n, endToEndSuccess: endSuccess / n, perNode: perNode, sinks: sinks };
  }

  return { makeRng: makeRng, sampleTask: sampleTask, simulateTokens: simulateTokens };
});
