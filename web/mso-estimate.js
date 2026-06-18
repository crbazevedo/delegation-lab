/**
 * mso-estimate.js — turn a practitioner's real pipeline into a cockpit graph.
 *
 * Accepts (auto-detected):
 *   1. Trace events:  [{task_id, node_id, outcome, corrected}, ...]
 *      or structured: [{task_id, path:[...], outcomes:{id:0/1}, corrected:{id:0/1}}]
 *      → estimates sigma_raw / sigma_corr / catch / masking PER NODE (the package's
 *        estimation), and infers edges from the order nodes appear in each task.
 *   2. LangGraph graph JSON (app.get_graph().to_json()):
 *      {nodes:[{id}], edges:[{source,target}]}  → structure + role-default numbers.
 *   3. Plain nodes: {nodes:[{id, sigma_skill?, catch_rate?, parents?, aggregation?}]}
 *
 * Estimation mirrors minimal_oversight.estimation: sigma_raw = mean(raw),
 * catch = (sigma_corr - sigma_raw)/(1 - sigma_raw), masking = sigma_corr/sigma_raw.
 * It maps an estimated sigma_raw back to the cockpit's sigma_skill via sigma_raw/γ
 * (γ = η/(η+δ) = 10/12), so the cockpit recomputes the same sigma_raw and masking.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.MSOEstimate = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var GAMMA = 10 / 12;
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function mean(a) { return a.length ? a.reduce(function (x, y) { return x + y; }, 0) / a.length : 0; }

  // Per-node estimation from paired raw/corrected outcome arrays.
  function estimate(raw, corr) {
    var sr = mean(raw), sc = corr.length ? mean(corr) : sr;
    var c = null;
    if (raw.length && corr.length && (1 - sr) >= 1e-8) c = clamp((sc - sr) / (1 - sr), 0, 1);
    return { sigma_raw: sr, sigma_corr: sc, masking: sr > 0 ? sc / sr : Infinity, catch: c, n: raw.length };
  }

  // Group flat events [{task_id,node_id,outcome,corrected}] into per-task traces.
  function eventsToTraces(events, opts) {
    opts = opts || {};
    var oF = opts.outcome_field || "outcome", cF = opts.corrected_field || "corrected", nF = opts.node_field || "node_id", tF = opts.task_field || "task_id";
    var byTask = {};
    events.forEach(function (e) {
      var t = String(e[tF] == null ? "t0" : e[tF]);
      (byTask[t] = byTask[t] || []).push(e);
    });
    return Object.keys(byTask).map(function (t) {
      var outcomes = {}, corrected = {}, path = [];
      byTask[t].forEach(function (e) {
        var id = String(e[nF]);
        if (path[path.length - 1] !== id) path.push(id);
        outcomes[id] = +e[oF] || 0;
        corrected[id] = e[cF] == null ? (+e[oF] || 0) : (+e[cF] || 0);
      });
      return { outcomes: outcomes, corrected: corrected, path: path };
    });
  }

  // Estimate per-node stats + infer parents from the order nodes appear in tasks.
  function fromTraces(traces) {
    var rawByNode = {}, corrByNode = {}, parents = {}, order = [];
    traces.forEach(function (tr) {
      var path = tr.path || Object.keys(tr.outcomes || {});
      path.forEach(function (id, i) {
        if (!rawByNode[id]) { rawByNode[id] = []; corrByNode[id] = []; parents[id] = {}; order.push(id); }
        if (tr.outcomes && tr.outcomes[id] != null) rawByNode[id].push(+tr.outcomes[id]);
        if (tr.corrected && tr.corrected[id] != null) corrByNode[id].push(+tr.corrected[id]);
        else if (tr.outcomes && tr.outcomes[id] != null) corrByNode[id].push(+tr.outcomes[id]);
        if (i > 0) parents[id][path[i - 1]] = true;
      });
    });
    return order.map(function (id) {
      var est = estimate(rawByNode[id], corrByNode[id]);
      return {
        id: id,
        sigma_skill: clamp(est.sigma_raw / GAMMA, 0.05, 0.98),
        catch_rate: est.catch == null ? 0.6 : est.catch,
        parents: Object.keys(parents[id]),
        aggregation: "product",
        type: typeFor(id),
        _est: est
      };
    });
  }

  // Map a node id to a cockpit connector type (for shape/colour).
  function typeFor(id) {
    var s = String(id).toLowerCase();
    if (/review|critic|judge|verify/.test(s)) return "reviewer";
    if (/human|approve|approver|sign/.test(s)) return "approver";
    if (/tool|search|retriev|rag|lookup|fetch|api/.test(s)) return "rag";
    if (/\bdb\b|datastore|database|store|memory/.test(s)) return "db";
    if (/classif|score|rank|route|triage|gate|merge|aggregate|intent/.test(s)) return "classifier";
    return "llm";
  }

  // Role defaults (keyword on node id), mirroring ROLE_DEFAULTS.
  function roleDefaults(id) {
    var s = String(id).toLowerCase();
    if (/review|critic|judge|verify|check/.test(s)) return { sigma_skill: 0.60, catch_rate: 0.75 };
    if (/human|approve|approver|sign.?off/.test(s)) return { sigma_skill: 0.85, catch_rate: 0.90 };
    if (/gate|merge|aggregate|combine|join/.test(s)) return { sigma_skill: 0.55, catch_rate: 0.65 };
    if (/tool|search|retriev|rag|api|db|datastore|lookup|fetch/.test(s)) return { sigma_skill: 0.80, catch_rate: 0.50 };
    return { sigma_skill: 0.55, catch_rate: 0.65 }; // generator
  }

  function fromLangGraph(g) {
    var rawNodes = g.nodes || [];
    var parents = {};
    (g.edges || []).forEach(function (e) {
      var src = e.source != null ? e.source : e.from, tgt = e.target != null ? e.target : e.to;
      if (src == null || tgt == null) return;
      (parents[tgt] = parents[tgt] || {})[src] = true;
    });
    return rawNodes.map(function (n) {
      var id = String(n.id != null ? n.id : n);
      var d = roleDefaults(id);
      return { id: id, sigma_skill: d.sigma_skill, catch_rate: d.catch_rate, parents: Object.keys(parents[id] || {}), aggregation: "product", type: typeFor(id) };
    }).filter(function (n) { return !/^__(start|end)__$/.test(n.id); });
  }

  function fromNodes(spec) {
    return (spec.nodes || []).map(function (n) {
      return {
        id: String(n.id),
        sigma_skill: n.sigma_skill == null ? 0.6 : n.sigma_skill,
        catch_rate: n.catch_rate == null ? 0.6 : n.catch_rate,
        parents: (n.parents || []).map(String),
        aggregation: n.aggregation || "product",
        type: n.type || typeFor(n.id)
      };
    });
  }

  // Main entry: parse arbitrary input text/JSON → cockpit nodes + a source label.
  function buildPipeline(input) {
    var data = typeof input === "string" ? JSON.parse(input) : input;
    if (Array.isArray(data)) {
      // events or structured traces
      var traces = (data.length && (data[0].node_id != null || data[0].nodeId != null))
        ? eventsToTraces(data, { node_field: data[0].node_id != null ? "node_id" : "nodeId" })
        : data;
      var nodes = fromTraces(traces);
      var totalN = nodes.reduce(function (s, n) { return s + (n._est ? n._est.n : 0); }, 0);
      return { nodes: nodes, source: "traces", note: nodes.length + " nodes · estimated from " + traces.length + " tasks (" + totalN + " observations)" };
    }
    if (data && Array.isArray(data.edges) && Array.isArray(data.nodes) && data.nodes.length && (data.nodes[0].id != null || typeof data.nodes[0] === "string") && !data.nodes[0].sigma_skill && !data.nodes[0].parents) {
      var lg = fromLangGraph(data);
      return { nodes: lg, source: "langgraph", note: lg.length + " nodes from graph structure · numbers are role defaults, tune or add traces" };
    }
    if (data && Array.isArray(data.nodes)) {
      // plain nodes; support top-level edges -> parents
      if (Array.isArray(data.edges)) {
        var par = {};
        data.edges.forEach(function (e) { var a = Array.isArray(e) ? e[0] : (e.source || e.from), b = Array.isArray(e) ? e[1] : (e.target || e.to); (par[b] = par[b] || {})[a] = true; });
        data.nodes.forEach(function (n) { if (!n.parents) n.parents = Object.keys(par[n.id] || {}); });
      }
      var nn = fromNodes(data);
      return { nodes: nn, source: "nodes", note: nn.length + " nodes loaded" };
    }
    throw new Error("Unrecognized format. Expected trace events, a LangGraph graph JSON, or {nodes:[...]}.");
  }

  // Layered left-to-right layout: x by longest-path depth, y spread within a layer.
  function layout(nodes, W, H) {
    W = W || 108; H = H || 40;
    var byId = {}; nodes.forEach(function (n) { byId[n.id] = n; });
    var depth = {}, visiting = {};
    function d(id) {
      if (depth[id] != null) return depth[id];
      if (visiting[id]) return 0;
      visiting[id] = true;
      var ps = (byId[id] && byId[id].parents) || [];
      var m = 0;
      ps.forEach(function (p) { if (byId[p]) m = Math.max(m, d(p) + 1); });
      visiting[id] = false; depth[id] = m; return m;
    }
    nodes.forEach(function (n) { d(n.id); });
    var rows = {};
    nodes.forEach(function (n) { var dp = depth[n.id]; rows[dp] = (rows[dp] || 0); n.x = 30 + dp * (W + 70); n.y = 40 + rows[dp] * (H + 38); rows[dp]++; });
    return nodes;
  }

  return { estimate: estimate, eventsToTraces: eventsToTraces, fromTraces: fromTraces, fromLangGraph: fromLangGraph, buildPipeline: buildPipeline, layout: layout };
});
