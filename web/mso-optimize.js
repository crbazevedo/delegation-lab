/**
 * mso-optimize.js — cost-aware allocation optimizer (browser port of optimize.py).
 *
 * Mirrors minimal_oversight.optimize + complexity exactly; pinned by the parity
 * test. Reuses mso-core.js for capacity propagation and mso-registry / mso-priors
 * for cost and competence. See docs/methodology/priors.md.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(
      require("./mso-core.js"), require("./mso-priors.js"), require("./mso-registry.js")
    );
  } else {
    root.MSO_Optimize = factory(root.MSO, root.MSO_Priors, root.MSO_Registry);
  }
})(typeof self !== "undefined" ? self : this, function (MSO, P, R) {
  "use strict";

  var GAMMA = 10 / 12;
  var GENERATOR_ROLES = { generator: 1, retriever: 1, reranker: 1, reader: 1, classifier: 1 };
  var DEFAULT_TOKENS = {
    generator: [1500, 500], reader: [3000, 600], classifier: [800, 50],
    retriever: [1000, 0], reranker: [4000, 0], reviewer: [1500, 300], corrector: [1800, 600],
  };
  var COMPLEXITY_FACTORS = { trivial: 1.0, easy: 0.95, moderate: 0.85, hard: 0.72, critical: 0.58 };

  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function complexityFactor(c) {
    if (c == null) c = "moderate";
    var f = COMPLEXITY_FACTORS[c];
    if (f == null) throw new Error("unknown complexity " + c);
    return f;
  }
  function effectiveSigma(prior, complexity, toolMisuse) {
    toolMisuse = toolMisuse || 0;
    return clamp(prior * complexityFactor(complexity) * (1 - toolMisuse), 0.01, 0.99);
  }
  function requiredPriorSigma(target, complexity, toolMisuse) {
    var denom = complexityFactor(complexity) * (1 - (toolMisuse || 0));
    return denom <= 0 ? Infinity : target / denom;
  }

  // ---- per-node parameters & cost ----
  function nodeParams(node) {
    var role = node.role || "generator";
    var task = node.task, model = node.model;
    var complexity = node.complexity || "moderate", misuse = node.tool_misuse || 0;

    // manual node (no model): use its explicit σ / catch / fix as-is
    if (!model && node.sigma_skill != null) {
      return [node.sigma_skill, node.catch_rate || 0.0,
              node.fix_rate != null ? node.fix_rate : 1.0];
    }

    if (role === "reviewer") {
      var b = (model ? P.priorMid(model, "review") : null); if (b == null) b = 0.62;
      return [0.92, effectiveSigma(b, complexity, misuse), 1.0];
    }
    if (role === "corrector") {
      var comp = (model ? P.priorMid(model, "drafting") : null); if (comp == null) comp = 0.85;
      var fix = clamp(0.70 * (comp / 0.85), 0.10, 0.95);
      return [0.92, 0.0, effectiveSigma(fix, complexity, misuse)];
    }
    if (role === "oversight") {
      var cb = (model ? P.priorMid(model, "review") : null); if (cb == null) cb = 0.62;
      var catch2 = effectiveSigma(cb, complexity, misuse);
      var cc = (model ? P.priorMid(model, "drafting") : null); if (cc == null) cc = 0.85;
      return [0.92, catch2, clamp(0.70 * (cc / 0.85), 0.10, 0.95)];
    }
    // generator family
    var base = (model && task) ? P.priorMid(model, task) : null; if (base == null) base = 0.50;
    var sr = effectiveSigma(base, complexity, misuse);
    var skill = clamp(sr / GAMMA, 0.05, 0.98);
    var ov = node.oversight_model;
    if (ov) {
      var ob = P.priorMid(ov, "review"); if (ob == null) ob = 0.62;
      var oc = effectiveSigma(ob, complexity, misuse);
      var od = P.priorMid(ov, "drafting"); if (od == null) od = 0.85;
      return [skill, oc, clamp(0.70 * (od / 0.85), 0.10, 0.95)];
    }
    return [skill, 0.0, 1.0];
  }

  function nodeCost(node) {
    var model = node.model;
    if (!model || !R.has(model)) return 0.0;
    var inTok = node.in_tok, outTok = node.out_tok;
    if (inTok == null || outTok == null) {
      var d = DEFAULT_TOKENS[node.role || "generator"] || [1500, 400];
      if (inTok == null) inTok = d[0];
      if (outTok == null) outTok = d[1];
    }
    var base = R.costPerRun(model, inTok, outTok);
    if (base == null) return 0.0;
    var calls = (node.calls == null ? 1.0 : node.calls) * (node.rework || 1);
    var cost = base * calls;
    var ov = node.oversight_model;
    if (ov && R.has(ov)) {
      var ovc = R.costPerRun(ov, inTok, outTok);
      if (ovc != null) cost += ovc * 2.0;
    }
    return cost;
  }
  function totalCost(nodes) { return nodes.reduce(function (s, n) { return s + nodeCost(n); }, 0); }

  function toPipeline(nodes) {
    return { nodes: nodes.map(function (n) {
      var p = nodeParams(n);
      var catch2 = p[1], k = (n.rework || 1);
      if (k > 1 && catch2 > 0) catch2 = 1 - Math.pow(1 - catch2, k);
      return { id: n.id, sigma_skill: p[0], catch_rate: catch2, fix_rate: p[2],
               parents: (n.parents || []).slice(), aggregation: n.aggregation || "product" };
    }) };
  }

  function cOp(nodes) {
    var pipe = toPipeline(nodes);
    var caps = MSO.computePipelineCapacity(pipe, { eta: 10, delta: 2, sigma_0: 0 });
    var childCount = {};
    pipe.nodes.forEach(function (n) { childCount[n.id] = 0; });
    pipe.nodes.forEach(function (n) { (n.parents || []).forEach(function (pp) { if (childCount[pp] != null) childCount[pp]++; }); });
    var sinks = pipe.nodes.filter(function (n) { return childCount[n.id] === 0; }).map(function (n) { return n.id; });
    if (!sinks.length) return 0.0;
    return Math.min.apply(null, sinks.map(function (s) { return caps[s]; }));
  }

  function evaluate(nodes, pMin, budget) {
    var c = cOp(nodes), cost = totalCost(nodes);
    return { c_op: c, cost: cost, feasible: c >= pMin,
             within_budget: (budget == null || cost <= budget) };
  }

  // ---- candidate models / prescription ----
  function candidateModels(task, complexity, toolMisuse, targetSigma) {
    targetSigma = targetSigma || 0;
    var pool = R.modelsByModality("llm").concat(R.modelsByModality("embedding")).concat(R.modelsByModality("reranker"));
    var opts = [];
    pool.forEach(function (model) {
      var base = P.priorMid(model, task);
      if (base == null) return;
      var m = R.get(model);
      if (m.blended == null) return;
      var seff = effectiveSigma(base, complexity, toolMisuse);
      opts.push({ model: model, sigma_eff: seff, cost_index: m.cost_index,
                  blended_usd: m.blended, open: m.open, clears: seff >= targetSigma });
    });
    opts.sort(function (a, b) {
      var ac = a.clears ? 0 : 1, bc = b.clears ? 0 : 1; if (ac !== bc) return ac - bc;
      var ai = a.cost_index == null ? 999 : a.cost_index, bi = b.cost_index == null ? 999 : b.cost_index;
      if (ai !== bi) return ai - bi;
      var ao = a.open ? 0 : 1, bo = b.open ? 0 : 1; if (ao !== bo) return ao - bo;
      return b.sigma_eff - a.sigma_eff;
    });
    return opts;
  }

  function prescribeNode(node, targetSigma) {
    var opts = candidateModels(node.task, node.complexity || "moderate", node.tool_misuse || 0, targetSigma);
    var clearing = opts.filter(function (o) { return o.clears; });
    var pick = clearing.length ? clearing[0] : (opts.length ? opts[0] : null);
    var openPick = clearing.filter(function (o) { return o.open; })[0] || null;
    var propPick = clearing.filter(function (o) { return !o.open; })[0] || null;
    return { pick: pick, oss_can_do: openPick != null, open_pick: openPick,
             proprietary_pick: propPick, needs_proprietary: (openPick == null && propPick != null),
             options: opts };
  }

  function genNodes(nodes) { return nodes.filter(function (n) { return GENERATOR_ROLES[n.role || "generator"]; }); }
  function swappable(nodes) {
    return nodes.filter(function (n) {
      return n.task && candidateModels(n.task, n.complexity || "moderate", n.tool_misuse || 0, 0).length;
    });
  }
  function strongOversightModel() {
    var best = "deepseek-v3", bs = -1;
    candidateModels("review", "moderate", 0, 0).forEach(function (o) { if (o.sigma_eff > bs) { best = o.model; bs = o.sigma_eff; } });
    return best;
  }
  function clone(nodes) { return nodes.map(function (n) { return Object.assign({}, n, { parents: (n.parents || []).slice() }); }); }
  function tupleGt(a, b) { if (a[0] !== b[0]) return a[0] > b[0]; return a[1] > b[1]; }

  function optimizeAllocation(nodes, pMin, budget, preferOss, maxSteps) {
    pMin = pMin == null ? 0.80 : pMin;
    maxSteps = maxSteps || 60;
    nodes = clone(nodes);
    var steps = [];

    genNodes(nodes).forEach(function (n) {
      if (!n.model) {
        var opts = candidateModels(n.task, n.complexity || "moderate", n.tool_misuse || 0, pMin);
        if (opts.length) { n.model = opts[0].model; steps.push("seed " + n.id + " → " + opts[0].model); }
      }
    });

    var i, e, best, baseC, baseCost, om;
    // Phase A: invest until feasible (max ΔC_op; cheaper breaks ties)
    for (i = 0; i < maxSteps; i++) {
      e = evaluate(nodes, pMin, budget);
      if (e.feasible) break;
      best = null; baseC = e.c_op; baseCost = e.cost;
      swappable(nodes).forEach(function (n) {
        candidateModels(n.task, n.complexity || "moderate", n.tool_misuse || 0, pMin).forEach(function (o) {
          if (o.model === n.model) return;
          var trial = clone(nodes);
          trial.forEach(function (t) { if (t.id === n.id) t.model = o.model; });
          var de = evaluate(trial, pMin, budget), dgain = de.c_op - baseC;
          if (dgain > 1e-6) {
            var key = [Math.round(dgain * 1e6) / 1e6, -(de.cost - baseCost)];
            if (best == null || tupleGt(key, best[0])) best = [key, trial, "upgrade " + n.id + " → " + o.model];
          }
        });
      });
      om = strongOversightModel();
      genNodes(nodes).forEach(function (n) {
        if (n.oversight_model) return;
        var trial = clone(nodes);
        trial.forEach(function (t) { if (t.id === n.id) t.oversight_model = om; });
        var de = evaluate(trial, pMin, budget), dgain = de.c_op - baseC;
        if (dgain > 1e-6) {
          var key = [Math.round(dgain * 1e6) / 1e6, -(de.cost - baseCost)];
          if (best == null || tupleGt(key, best[0])) best = [key, trial, "add review+correct at " + n.id + " (" + om + ")"];
        }
      });
      if (best == null) break;
      nodes = best[1]; steps.push(best[2]);
    }

    // Phase B: divest while feasible (biggest cost cut)
    for (i = 0; i < maxSteps; i++) {
      e = evaluate(nodes, pMin, budget);
      if (!e.feasible) break;
      best = null; baseCost = e.cost;
      swappable(nodes).forEach(function (n) {
        candidateModels(n.task, n.complexity || "moderate", n.tool_misuse || 0, pMin).forEach(function (o) {
          if (o.model === n.model) return;
          var trial = clone(nodes);
          trial.forEach(function (t) { if (t.id === n.id) t.model = o.model; });
          var de = evaluate(trial, pMin, budget), saving = baseCost - de.cost;
          if (de.feasible && saving > 1e-9) {
            var bonus = o.open ? 1e-9 : 0.0;
            if (best == null || (saving + bonus) > best[0]) best = [saving + bonus, trial, "downgrade " + n.id + " → " + o.model];
          }
        });
      });
      nodes.forEach(function (n) {
        if (!n.oversight_model) return;
        var trial = clone(nodes);
        trial.forEach(function (t) { if (t.id === n.id) delete t.oversight_model; });
        var de = evaluate(trial, pMin, budget), saving = baseCost - de.cost;
        if (de.feasible && saving > 1e-9 && (best == null || saving > best[0])) best = [saving, trial, "drop review+correct at " + n.id];
        candidateModels("review", n.complexity || "moderate", n.tool_misuse || 0, 0).forEach(function (o) {
          if (o.model === n.oversight_model) return;
          var tr2 = clone(nodes);
          tr2.forEach(function (t) { if (t.id === n.id) t.oversight_model = o.model; });
          var de2 = evaluate(tr2, pMin, budget), sv2 = baseCost - de2.cost;
          if (de2.feasible && sv2 > 1e-9 && (best == null || sv2 > best[0])) best = [sv2, tr2, "cheaper review at " + n.id + " → " + o.model];
        });
      });
      if (best == null) break;
      nodes = best[1]; steps.push(best[2]);
    }

    e = evaluate(nodes, pMin, budget);
    return { nodes: nodes, c_op: e.c_op, cost: e.cost, feasible: e.feasible,
             within_budget: e.within_budget, p_min: pMin, budget: budget == null ? null : budget, steps: steps };
  }

  return {
    GAMMA: GAMMA, complexityFactor: complexityFactor, effectiveSigma: effectiveSigma,
    requiredPriorSigma: requiredPriorSigma, nodeParams: nodeParams, nodeCost: nodeCost,
    totalCost: totalCost, cOp: cOp, evaluate: evaluate, candidateModels: candidateModels,
    prescribeNode: prescribeNode, optimizeAllocation: optimizeAllocation,
  };
});
