/**
 * mso-core.js — browser port of the Minimum Sufficient Oversight equations.
 *
 * This is a faithful re-implementation of the closed forms in
 * `src/minimal_oversight/_formulae.py` and the capacity propagation in
 * `src/minimal_oversight/capacity.py`. Every function here is pinned to the
 * Python reference by `tests/test_parity.py` (|Δ| < 1e-6). Do not edit the
 * math without updating the parity fixtures.
 *
 * Reference: "Minimal Oversight: Uncertainty-Aware Governance for Delegated
 * AI Systems" (Azevedo, 2026). Equation numbers cited per function.
 *
 * Usage (browser):   <script src="mso-core.js"></script> then window.MSO
 * Usage (node):      const MSO = require('./mso-core.js')
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.MSO = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var EPS = 1e-10;
  function clip(x, a, b) { return Math.max(a, Math.min(b, x)); }

  // Fisher information for Bernoulli outcomes: g(σ) = 1/[σ(1−σ)] (Eq. 3)
  function fisherInformation(sigma) {
    var s = clip(sigma, EPS, 1 - EPS);
    return 1 / (s * (1 - s));
  }
  // Volume element √g = 1/√(σ(1−σ)) — cost weight in the MSO
  function fisherVolumeElement(sigma) {
    var s = clip(sigma, EPS, 1 - EPS);
    return 1 / Math.sqrt(s * (1 - s));
  }

  // Fixed-point raw competence: σ*_raw = (η·σ_skill + δ·σ₀)/(η+δ) (Eq. 5)
  function sigmaRawFixedPoint(sigmaSkill, eta, delta, sigma0) {
    eta = eta == null ? 10 : eta;
    delta = delta == null ? 2 : delta;
    sigma0 = sigma0 == null ? 0 : sigma0;
    var denom = eta + delta;
    if (denom <= 0) throw new Error("eta + delta must be positive");
    return (eta * sigmaSkill + delta * sigma0) / denom;
  }
  // Fixed-point corrected quality: σ*_corr = σ_raw + (1−σ_raw)·c (Eq. 6)
  function sigmaCorrFixedPoint(sigmaRaw, catchRate) {
    return sigmaRaw + (1 - sigmaRaw) * catchRate;
  }
  // Masking index M* = σ_corr/σ_raw; > 1 indicates masking
  function maskingIndex(sigmaCorr, sigmaRaw) {
    if (sigmaRaw <= 0) return Infinity;
    return sigmaCorr / sigmaRaw;
  }

  // Effective skill with upstream quality: σ_skill·AGG(parents) (Eq. 7)
  function effectiveSkill(sigmaSkill, parentSigmaCorrs, aggregation) {
    if (!parentSigmaCorrs || parentSigmaCorrs.length === 0) return sigmaSkill;
    var agg = aggregation || "product";
    var v;
    if (agg === "product") v = parentSigmaCorrs.reduce(function (a, b) { return a * b; }, 1);
    else if (agg === "min" || agg === "weakest_link") v = Math.min.apply(null, parentSigmaCorrs);
    else if (agg === "mean" || agg === "weighted_mean") v = parentSigmaCorrs.reduce(function (a, b) { return a + b; }, 0) / parentSigmaCorrs.length;
    else throw new Error("Unknown aggregation: " + agg);
    return sigmaSkill * v;
  }

  // Euler-Lagrange water-filling: α*(x) = min(α_max, (λ/2)·σ_raw·√(σ_raw(1−σ_raw))) (Eq. 8)
  function optimalAuthority(sigmaRaw, lam, alphaMax) {
    alphaMax = alphaMax == null ? 1 : alphaMax;
    return sigmaRaw.map(function (v) {
      var s = clip(v, EPS, 1 - EPS);
      return Math.min((lam / 2) * s * Math.sqrt(s * (1 - s)), alphaMax);
    });
  }
  // Bisection for the Lagrange multiplier λ meeting ∫α*·σ_raw ≥ p_min·|S|
  function solveLambda(sigmaRaw, pMin, alphaMax, tol, maxIter) {
    alphaMax = alphaMax == null ? 1 : alphaMax;
    tol = tol == null ? 1e-8 : tol;
    maxIter = maxIter == null ? 200 : maxIter;
    var sigma = sigmaRaw.map(Number);
    var n = sigma.length;
    var target = pMin * n;
    function delivery(lam) {
      var a = optimalAuthority(sigma, lam, alphaMax);
      var s = 0;
      for (var i = 0; i < n; i++) s += a[i] * sigma[i];
      return s;
    }
    var lo = 0, hi = 1;
    for (var k = 0; k < 50; k++) { if (delivery(hi) >= target) break; hi *= 2; }
    for (var j = 0; j < maxIter; j++) {
      var mid = (lo + hi) / 2;
      var d = delivery(mid);
      if (Math.abs(d - target) < tol) break;
      if (d < target) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  }
  // Solve the MSO: α*, water level λ, governance cost ∫α²√g, delivery ∫α·σ
  function solveMSO(sigmaRaw, pMin, alphaMax) {
    alphaMax = alphaMax == null ? 1 : alphaMax;
    var sigma = sigmaRaw.map(Number);
    var lam = solveLambda(sigma, pMin, alphaMax);
    var alpha = optimalAuthority(sigma, lam, alphaMax);
    var cost = 0, deliv = 0;
    for (var i = 0; i < sigma.length; i++) {
      cost += alpha[i] * alpha[i] * fisherVolumeElement(sigma[i]);
      deliv += alpha[i] * sigma[i];
    }
    return { alphaStar: alpha, sigmaRaw: sigma, lam: lam, totalCost: cost, delivery: deliv };
  }

  // Effective autonomy buffer: B_eff = C_op − p_min − λH(W) (Eq. 16)
  function effectiveAutonomyBuffer(cOp, pMin, lam, hW) { return cOp - pMin - lam * hW; }
  // Autonomy time: T*_auto = B_eff/μ_eff (Eq. 17)
  function autonomyTime(cOp, pMin, lam, hW, muEff) {
    var b = effectiveAutonomyBuffer(cOp, pMin, lam, hW);
    if (muEff <= 0) return b > 0 ? Infinity : 0;
    return Math.max(b / muEff, 0);
  }
  // Capacity cliff: H_crit = (C_op − p_min)/λ
  function criticalEntropy(cOp, pMin, lam) {
    if (lam <= 0) return Infinity;
    return (cOp - pMin) / lam;
  }
  // Single-node capacity C = η/(η+δ) at σ_skill = 1 (Eq. 10 + Eq. 5)
  function nodeCapacity(eta, delta, sigma0) { return sigmaRawFixedPoint(1, eta, delta, sigma0 || 0); }
  // SOTA priority proxy: S(v) = DC(v)·M*(v)·κ(v)
  function sotaPriorityScore(dc, masking, kappa) { return dc * masking * kappa; }

  // ---- Pipeline propagation (mirrors capacity.compute_pipeline_capacity) ----
  function topoOrder(nodes) {
    var indeg = {}, children = {};
    nodes.forEach(function (n) { indeg[n.id] = (n.parents || []).length; children[n.id] = []; });
    nodes.forEach(function (n) { (n.parents || []).forEach(function (p) { children[p].push(n.id); }); });
    var q = nodes.filter(function (n) { return indeg[n.id] === 0; }).map(function (n) { return n.id; });
    var order = [];
    while (q.length) {
      var id = q.shift();
      order.push(id);
      children[id].forEach(function (c) { if (--indeg[c] === 0) q.push(c); });
    }
    return order;
  }
  function computePipelineCapacity(pipeline, opts) {
    opts = opts || {};
    var eta = opts.eta == null ? 10 : opts.eta;
    var delta = opts.delta == null ? 2 : opts.delta;
    var s0 = opts.sigma_0 == null ? 0 : opts.sigma_0;
    var nodes = pipeline.nodes, byId = {};
    nodes.forEach(function (n) { byId[n.id] = n; });
    var corr = {}, caps = {};
    topoOrder(nodes).forEach(function (id) {
      var n = byId[id];
      var skill = n.sigma_skill == null ? 0.55 : n.sigma_skill;
      var c = n.catch_rate == null ? 0.65 : n.catch_rate;
      var parents = n.parents || [];
      var skillEff;
      if (parents.length) {
        var pc = parents.map(function (p) { return corr[p] == null ? 1.0 : corr[p]; });
        skillEff = effectiveSkill(skill, pc, n.aggregation || "product");
      } else skillEff = skill;
      var sr = sigmaRawFixedPoint(skillEff, eta, delta, s0);
      var sc = sigmaCorrFixedPoint(sr, c);
      corr[id] = sc; caps[id] = sc;
    });
    return caps;
  }
  // One-call analysis: feasibility ceiling, bottleneck, buffer, cliff, per-node masking
  function analyzePipeline(pipeline, opts) {
    opts = opts || {};
    var pmin = opts.p_min == null ? 0.80 : opts.p_min;
    var eta = opts.eta == null ? 10 : opts.eta;
    var delta = opts.delta == null ? 2 : opts.delta;
    var s0 = opts.sigma_0 == null ? 0 : opts.sigma_0;
    var gg = opts.governance_gap == null ? 0.02 : opts.governance_gap;
    var hw = opts.process_entropy == null ? 0 : opts.process_entropy;
    var nodes = pipeline.nodes;
    var caps = computePipelineCapacity(pipeline, { eta: eta, delta: delta, sigma_0: s0 });
    var childCount = {};
    nodes.forEach(function (n) { childCount[n.id] = 0; });
    nodes.forEach(function (n) { (n.parents || []).forEach(function (p) { childCount[p]++; }); });
    var sinks = nodes.filter(function (n) { return childCount[n.id] === 0; }).map(function (n) { return n.id; });
    var cop = Math.min.apply(null, sinks.map(function (s) { return caps[s]; }));
    var bott = nodes[0].id;
    nodes.forEach(function (n) { if (caps[n.id] < caps[bott]) bott = n.id; });
    var beff = effectiveAutonomyBuffer(cop, pmin, gg, hw);
    var hcrit = criticalEntropy(cop, pmin, gg);
    var perNode = {};
    nodes.forEach(function (n) {
      var c = n.catch_rate == null ? 0.65 : n.catch_rate;
      var lsr = sigmaRawFixedPoint(n.sigma_skill == null ? 0.55 : n.sigma_skill, eta, delta, s0);
      var lsc = sigmaCorrFixedPoint(lsr, c);
      perNode[n.id] = {
        sigma_raw: lsr, sigma_corr: lsc, masking: maskingIndex(lsc, lsr),
        fisher: fisherInformation(lsr), capacity: caps[n.id]
      };
    });
    return { cop: cop, bottleneck: bott, beff: beff, hcrit: hcrit, feasible: cop >= pmin, perNode: perNode, capacities: caps };
  }

  return {
    fisherInformation: fisherInformation, fisherVolumeElement: fisherVolumeElement,
    sigmaRawFixedPoint: sigmaRawFixedPoint, sigmaCorrFixedPoint: sigmaCorrFixedPoint,
    maskingIndex: maskingIndex, effectiveSkill: effectiveSkill,
    optimalAuthority: optimalAuthority, solveLambda: solveLambda, solveMSO: solveMSO,
    effectiveAutonomyBuffer: effectiveAutonomyBuffer, autonomyTime: autonomyTime,
    criticalEntropy: criticalEntropy, nodeCapacity: nodeCapacity, sotaPriorityScore: sotaPriorityScore,
    computePipelineCapacity: computePipelineCapacity, analyzePipeline: analyzePipeline, topoOrder: topoOrder
  };
});
