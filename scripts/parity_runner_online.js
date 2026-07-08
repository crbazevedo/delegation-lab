/**
 * parity_runner_online.js — compute adaptive-online.js outputs for shared inputs.
 *
 * Invoked by tests/test_parity_online.py:  node scripts/parity_runner_online.js <in.json> <out.json>
 * The Python side computes the same outputs from the SAME inputs with the installed
 * `minimal_oversight` package (skirental / tracking / caching) plus the full-instance
 * forms in scripts/online_skirental.py, and asserts |Δ| < 1e-6. This pins the browser
 * port of the online variants to the Python reference.
 *
 * Only DETERMINISTIC quantities are pinned. MARKER eviction is randomized and NOT
 * NumPy-compatible, so it is exercised by adaptive-online's own bound checks, not here.
 */
const fs = require("fs");
const O = require("../web/adaptive-online.js");

const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = {};

// --- ski-rental: per-phase closed forms (skirental.py) ---
out.sk_dwell = cases.sk_lam.map((lam) => O.skirentalDwell(lam));
out.sk_ratio = cases.sk_lam.map((lam) => O.skirentalRatio(lam));
out.opt_slack = cases.slack.map((a) => O.optSlackCost(a.tau, a.lam));
out.dwell_slack = cases.dwell_slack.map((a) => O.dwellSlackCost(a.tau, a.lam, a.d));
out.worst_case = cases.worst.map((a) => O.worstCaseRatio(a.d, a.lam, a.tau_max));
out.minimax = cases.minimax.map((a) => {
  const m = O.minimaxDwell(a.lam);
  return { dwell: m.dwell, ratio: m.ratio };
});

// --- ski-rental: full-instance simulation (scripts/online_skirental.py) ---
out.opt_cost = cases.instance.map((a) => O.optCost(a.W, a.tau, a.lam, a.ncyc));
out.dwell_cost = cases.instance.map((a) => O.dwellCost(a.W, a.tau, a.lam, a.ncyc, a.d));
out.cr_ratchet = cases.instance.map((a) => O.instanceCR("ratchet", a.W, a.tau, a.lam, a.ncyc));
out.cr_dwell = cases.instance.map((a) => O.instanceCR("dwell", a.W, a.tau, a.lam, a.ncyc, { dwell: a.d }));

// --- tracking (tracking.py) ---
out.kal_var = cases.tracking.map((a) => O.kalmanSteadystateVar(a.nu, a.sigma));
out.matched = cases.tracking.map((a) => O.matchedMargin(O.kalmanSteadystateVar(a.nu, a.sigma)));
out.floor = cases.tracking.map((a) => O.noiseFloorPerStep(a.nu, a.sigma));
out.deadband = cases.tracking.map((a) => O.deadbandMargin(a.sigma));
out.kal_track = cases.kalman_seq.map((c) => {
  const kt = new O.KalmanTracker(c.nu, c.sigma, c.xhat);
  return c.obs.map((o) => kt.update(o));
});

// --- caching: deterministic forms (caching.py) ---
out.pool_cap = cases.pool.map((a) => O.poolCapacity(a.c, a.b));
out.lru = cases.requests.map((rq) => O.lruMisses(rq.req, rq.h));
out.belady = cases.requests.map((rq) => O.beladyMisses(rq.req, rq.h));
out.ratchet_demand = cases.requests.map((rq) => O.ratchetDemand(rq.req));
out.cr_lru = cases.requests.map((rq) => O.competitiveRatio("lru", rq.req, rq.h));
out.cyclic_len = cases.cyclic.map((a) => O.cyclicAdversary(a.h, a.rounds).length);

fs.writeFileSync(process.argv[3], JSON.stringify(out));
