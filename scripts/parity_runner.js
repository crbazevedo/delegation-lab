/**
 * parity_runner.js — compute mso-core.js outputs for a shared set of inputs.
 *
 * Invoked by tests/test_parity.py:  node scripts/parity_runner.js <in.json> <out.json>
 * The Python side computes the same outputs with the installed `minimal_oversight`
 * package and asserts they agree to within 1e-6. This pins the browser port to the
 * paper's reference implementation.
 */
const fs = require("fs");
const MSO = require("../web/mso-core.js");
const MSOEstimate = require("../web/mso-estimate.js");
const MSO_Priors = require("../web/mso-priors.js");

const inPath = process.argv[2];
const outPath = process.argv[3];
const cases = JSON.parse(fs.readFileSync(inPath, "utf8"));

const out = {};

out.fisher = cases.fisher.map((s) => MSO.fisherInformation(s));
out.volume = cases.volume.map((s) => MSO.fisherVolumeElement(s));
out.sraw_fp = cases.sraw_fp.map((a) => MSO.sigmaRawFixedPoint(a[0], a[1], a[2], a[3]));
out.scorr = cases.scorr.map((a) => MSO.sigmaCorrFixedPoint(a[0], a[1], a[2]));
out.masking = cases.masking.map((a) => MSO.maskingIndex(a[0], a[1]));
out.estimate = (cases.estimate || []).map((c) => {
  const e = MSOEstimate.estimate(c.raw, c.corr);
  return { sigma_raw: e.sigma_raw, sigma_corr: e.sigma_corr, masking: e.masking, catch: e.catch };
});
out.eff_skill = cases.eff_skill.map((a) => MSO.effectiveSkill(a[0], a[1], a[2]));
out.opt_auth = cases.opt_auth.map((a) => MSO.optimalAuthority(a[0], a[1], a[2]));
out.solve_lambda = cases.solve_lambda.map((a) => {
  const lam = MSO.solveLambda(a[0], a[1]);
  return { lam: lam, alpha: MSO.optimalAuthority(a[0], lam) };
});
out.buffer = cases.buffer.map((a) => MSO.effectiveAutonomyBuffer(a[0], a[1], a[2], a[3]));
out.autonomy = cases.autonomy.map((a) => MSO.autonomyTime(a[0], a[1], a[2], a[3], a[4]));
out.crit_entropy = cases.crit_entropy.map((a) => MSO.criticalEntropy(a[0], a[1], a[2]));
out.ro_step = cases.ro_step.map((a) => MSO.returnOperatorStep(a[0], a[1], a[2], a[3], a[4], a[5]));
out.scope = cases.scope.map((c) => {
  const r = MSO.selectScope(c.sigma, c.p_min, c.coverage);
  return { delegated: r.delegated_tasks, coverage: r.coverage, cost: r.total_cost, avg: r.avg_sigma_delegated };
});
out.ro_traj = cases.ro_traj.map((c) => {
  let s = c.init;
  for (let i = 0; i < c.steps; i++) s = MSO.returnOperatorStep(s, c.skill, c.eta, c.delta, c.dt, c.sigma0);
  return s;
});

out.pipelines = cases.pipelines.map((pc) => {
  const r = MSO.analyzePipeline(pc.pipeline, { p_min: pc.p_min, process_entropy: pc.hw });
  const masking = {};
  Object.keys(r.perNode).forEach((k) => { masking[k] = r.perNode[k].masking; });
  return { cop: r.cop, beff: r.beff, hcrit: r.hcrit, bottleneck: r.bottleneck, feasible: r.feasible, masking: masking };
});

out.centrality = cases.centrality.map((c) => c.names.map((n) => MSO.delegationCentrality(c.pipeline, n)));
out.motifs = cases.motifs.map((p) => MSO.detectMotifs(p).map((mi) => mi.risk_description).sort());
out.risk = cases.risk.map((p) => MSO.rankNodesByRisk(p).map((r) => ({
  name: r.name, sota: r.sota_score, dc: r.delegation_centrality, masking: r.masking_index,
  fi: r.fan_in_degree, fo: r.fan_out_degree, bott: r.is_bottleneck,
})));

out.seed_node = (cases.seed_node || []).map((c) => {
  const s = MSO_Priors.seedNode(c.model, c.task_type);
  const p = s.provenance;
  return {
    seeds: s.seeds,
    sigma_skill: s.sigma_skill != null ? s.sigma_skill : null,
    catch_rate: s.catch_rate != null ? s.catch_rate : null,
    fix_rate: s.fix_rate != null ? s.fix_rate : null,
    confidence: p.confidence,
    band_low: p.band.low,
    band_mid: p.band.mid,
    band_high: p.band.high,
  };
});

fs.writeFileSync(outPath, JSON.stringify(out));
