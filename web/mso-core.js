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
  // Fixed-point corrected quality: σ*_corr = σ_raw + (1−σ_raw)·c_eff (Eq. 6).
  // c_eff = catchRate (reviewer detection) × fixRate (corrector repair).
  // fixRate defaults to 1 → the paper's single-number model (caught == fixed).
  function sigmaCorrFixedPoint(sigmaRaw, catchRate, fixRate) {
    var f = fixRate == null ? 1 : fixRate;
    return sigmaRaw + (1 - sigmaRaw) * catchRate * f;
  }
  // Masking index M* = σ_corr/σ_raw; > 1 indicates masking
  function maskingIndex(sigmaCorr, sigmaRaw) {
    if (sigmaRaw <= 0) return Infinity;
    return sigmaCorr / sigmaRaw;
  }

  // One Euler step of the Return Operator ODE: dσ/dt = η(σ_skill,eff − σ) − δ(σ − σ₀) (Eq. 4)
  function returnOperatorStep(sigma, sigmaSkillEff, eta, delta, dt, sigma0) {
    sigma0 = sigma0 == null ? 0 : sigma0;
    var dsigma = eta * (sigmaSkillEff - sigma) - delta * (sigma - sigma0);
    return sigma + dsigma * dt;
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
  // Endogenous scope selection: which tasks to delegate (mirrors allocation.select_scope)
  function selectScope(sigmaRaw, pMin, coverageMin, alphaMax) {
    coverageMin = coverageMin == null ? 0 : coverageMin;
    alphaMax = alphaMax == null ? 1 : alphaMax;
    var sigma = sigmaRaw.map(Number), n = sigma.length;
    var eff = sigma.map(function (v) { var s = clip(v, EPS, 1 - EPS); return s * Math.sqrt(s * (1 - s)); });
    var order = sigma.map(function (_, i) { return i; }).sort(function (a, b) { return eff[b] - eff[a]; });
    var minCount = Math.max(1, Math.ceil(coverageMin * n));
    var delegated = order.slice(0, minCount);
    for (var k = minCount; k < order.length; k++) { if (sigma[order[k]] >= pMin * 0.8) delegated.push(order[k]); }
    var set = {}; delegated.forEach(function (i) { set[i] = true; });
    var excluded = []; for (var j = 0; j < n; j++) if (!set[j]) excluded.push(j);
    var totalCost = 0, avg = 0;
    if (delegated.length) {
      var sub = delegated.map(function (i) { return sigma[i]; });
      totalCost = solveMSO(sub, pMin, alphaMax).totalCost;
      avg = sub.reduce(function (a, b) { return a + b; }, 0) / sub.length;
    }
    return {
      delegated_tasks: delegated.slice().sort(function (a, b) { return a - b; }),
      excluded_tasks: excluded, coverage: n > 0 ? delegated.length / n : 0,
      total_cost: totalCost, avg_sigma_delegated: avg
    };
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
      var f = n.fix_rate == null ? 1 : n.fix_rate;
      var parents = n.parents || [];
      var skillEff;
      if (parents.length) {
        var pc = parents.map(function (p) { return corr[p] == null ? 1.0 : corr[p]; });
        skillEff = effectiveSkill(skill, pc, n.aggregation || "product");
      } else skillEff = skill;
      var sr = sigmaRawFixedPoint(skillEff, eta, delta, s0);
      var sc = sigmaCorrFixedPoint(sr, c, f);
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
      var f = n.fix_rate == null ? 1 : n.fix_rate;
      var lsr = sigmaRawFixedPoint(n.sigma_skill == null ? 0.55 : n.sigma_skill, eta, delta, s0);
      var lsc = sigmaCorrFixedPoint(lsr, c, f);
      perNode[n.id] = {
        sigma_raw: lsr, sigma_corr: lsc, masking: maskingIndex(lsc, lsr),
        fisher: fisherInformation(lsr), capacity: caps[n.id]
      };
    });
    return { cop: cop, bottleneck: bott, beff: beff, hcrit: hcrit, feasible: cop >= pmin, perNode: perNode, capacities: caps };
  }

  // ---- Topology (mirrors topology.py: motifs, centrality, risk ranking) ----
  function _maps(nodes) {
    var children = {}, parents = {};
    nodes.forEach(function (n) { children[n.id] = []; parents[n.id] = (n.parents || []).slice(); });
    nodes.forEach(function (n) { (n.parents || []).forEach(function (p) { if (children[p]) children[p].push(n.id); }); });
    return { children: children, parents: parents };
  }
  function _reach(start, adj) {
    var seen = {}, q = (adj[start] || []).slice();
    while (q.length) {
      var x = q.shift();
      if (seen[x]) continue;
      seen[x] = true;
      (adj[x] || []).forEach(function (y) { if (!seen[y]) q.push(y); });
    }
    delete seen[start];
    return seen;
  }
  function _dist(start, adj) {
    var d = {}; d[start] = 0; var q = [start];
    while (q.length) {
      var x = q.shift();
      (adj[x] || []).forEach(function (y) { if (d[y] == null) { d[y] = d[x] + 1; q.push(y); } });
    }
    return d;
  }
  // Delegation centrality DC(v): fan-out degree weighted by inverse downstream distance
  function delegationCentrality(pipeline, name) {
    var m = _maps(pipeline.nodes);
    var outDeg = (m.children[name] || []).length;
    var desc = _reach(name, m.children);
    if (Object.keys(desc).length === 0) return outDeg;
    var d = _dist(name, m.children), weighted = 0;
    Object.keys(d).forEach(function (n) { if (n !== name && d[n] > 0) weighted += 1 / d[n]; });
    return outDeg * (1 + weighted);
  }
  // Detect canonical delegation motifs (Table 2): single, chain, fan_out, merge, diamond
  function detectMotifs(pipeline) {
    var nodes = pipeline.nodes, m = _maps(nodes), ids = nodes.map(function (n) { return n.id; });
    var inDeg = {}, outDeg = {};
    ids.forEach(function (id) { inDeg[id] = m.parents[id].length; outDeg[id] = m.children[id].length; });
    var motifs = [];
    if (ids.length === 1) {
      return [{ motif: "single", nodes: [ids[0]], risk_description: "Single delegation. Baseline masking applies." }];
    }
    var chainNodes = {};
    ids.forEach(function (id) { if (inDeg[id] === 1 && outDeg[id] === 1) chainNodes[id] = true; });
    var visited = {};
    topoOrder(nodes).forEach(function (node) {
      if (visited[node] || !chainNodes[node]) return;
      var chain = [node]; visited[node] = true; var cur = node;
      while (true) {
        var succ = m.children[cur];
        if (succ.length === 1 && chainNodes[succ[0]] && !visited[succ[0]]) { chain.push(succ[0]); visited[succ[0]] = true; cur = succ[0]; }
        else break;
      }
      if (chain.length >= 2) motifs.push({ motif: "chain", nodes: chain, risk_description: "Chain of depth " + chain.length + ". Masking and quality loss accumulate with depth. Improve upstream quality first." });
    });
    ids.forEach(function (name) {
      if (outDeg[name] > 1) motifs.push({ motif: "fan_out", nodes: [name].concat(m.children[name]), risk_description: "Fan-out at " + name + " (degree " + outDeg[name] + "). One failure contaminates multiple branches. Prioritize this node for review." });
    });
    ids.forEach(function (name) {
      if (inDeg[name] > 1) motifs.push({ motif: "merge", nodes: m.parents[name].concat([name]), risk_description: "Merge at " + name + " (fan-in " + inDeg[name] + "). Throughput and autonomy limited by bottleneck path. Aggregation type determines masking severity." });
    });
    ids.forEach(function (name) {
      if (inDeg[name] < 2) return;
      var parents = m.parents[name];
      for (var i = 0; i < parents.length; i++) for (var j = i + 1; j < parents.length; j++) {
        var p1 = parents[i], p2 = parents[j];
        var a1 = _reach(p1, m.parents), a2 = _reach(p2, m.parents), shared = {};
        Object.keys(a1).forEach(function (k) { if (a2[k]) shared[k] = true; });
        if (a2[p1]) shared[p1] = true;
        if (a1[p2]) shared[p2] = true;
        var sk = Object.keys(shared);
        if (sk.length) {
          var source = sk[0], best = -1;
          sk.forEach(function (s) { var dd = _dist(s, m.children); var L = dd[name] == null ? -1 : dd[name]; if (L > best) { best = L; source = s; } });
          motifs.push({ motif: "diamond", nodes: [source, p1, p2, name], risk_description: "Diamond: " + source + " → {" + p1 + ", " + p2 + "} → " + name + ". Correlated upstream errors create conditional fragility. Correct the shared source rather than hardening the merge." });
        }
      }
    });
    return motifs;
  }
  // Rank nodes by governance risk: SOTA score S = DC·M*·κ, then delegation centrality
  function rankNodesByRisk(pipeline, opts) {
    opts = opts || {};
    var eta = opts.eta == null ? 10 : opts.eta, delta = opts.delta == null ? 2 : opts.delta, s0 = opts.sigma_0 == null ? 0 : opts.sigma_0;
    var m = _maps(pipeline.nodes);
    var motifs = detectMotifs(pipeline), nodeMotifs = {};
    pipeline.nodes.forEach(function (n) { nodeMotifs[n.id] = {}; });
    motifs.forEach(function (mi) { mi.nodes.forEach(function (n) { if (nodeMotifs[n]) nodeMotifs[n][mi.motif] = true; }); });
    var risks = pipeline.nodes.map(function (n) {
      var dc = delegationCentrality(pipeline, n.id);
      var skill = n.sigma_skill == null ? 0.55 : n.sigma_skill, c = n.catch_rate == null ? 0.65 : n.catch_rate;
      var lsr = sigmaRawFixedPoint(skill, eta, delta, s0), lsc = sigmaCorrFixedPoint(lsr, c), mstar = maskingIndex(lsc, lsr);
      var sota = dc * mstar * (1 - skill);
      return {
        name: n.id, delegation_centrality: dc, masking_index: mstar, sota_score: sota,
        fan_out_degree: m.children[n.id].length, fan_in_degree: m.parents[n.id].length,
        is_bottleneck: m.parents[n.id].length > 1, motifs: Object.keys(nodeMotifs[n.id])
      };
    });
    risks.sort(function (a, b) { return b.sota_score !== a.sota_score ? b.sota_score - a.sota_score : b.delegation_centrality - a.delegation_centrality; });
    return risks;
  }

  return {
    fisherInformation: fisherInformation, fisherVolumeElement: fisherVolumeElement,
    delegationCentrality: delegationCentrality, detectMotifs: detectMotifs, rankNodesByRisk: rankNodesByRisk,
    sigmaRawFixedPoint: sigmaRawFixedPoint, sigmaCorrFixedPoint: sigmaCorrFixedPoint,
    maskingIndex: maskingIndex, returnOperatorStep: returnOperatorStep, effectiveSkill: effectiveSkill,
    optimalAuthority: optimalAuthority, solveLambda: solveLambda, solveMSO: solveMSO, selectScope: selectScope,
    effectiveAutonomyBuffer: effectiveAutonomyBuffer, autonomyTime: autonomyTime,
    criticalEntropy: criticalEntropy, nodeCapacity: nodeCapacity, sotaPriorityScore: sotaPriorityScore,
    computePipelineCapacity: computePipelineCapacity, analyzePipeline: analyzePipeline, topoOrder: topoOrder
  };
});
