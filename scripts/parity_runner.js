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

const inPath = process.argv[2];
const outPath = process.argv[3];
const cases = JSON.parse(fs.readFileSync(inPath, "utf8"));

const out = {};

out.fisher = cases.fisher.map((s) => MSO.fisherInformation(s));
out.volume = cases.volume.map((s) => MSO.fisherVolumeElement(s));
out.sraw_fp = cases.sraw_fp.map((a) => MSO.sigmaRawFixedPoint(a[0], a[1], a[2], a[3]));
out.scorr = cases.scorr.map((a) => MSO.sigmaCorrFixedPoint(a[0], a[1]));
out.masking = cases.masking.map((a) => MSO.maskingIndex(a[0], a[1]));
out.eff_skill = cases.eff_skill.map((a) => MSO.effectiveSkill(a[0], a[1], a[2]));
out.opt_auth = cases.opt_auth.map((a) => MSO.optimalAuthority(a[0], a[1], a[2]));
out.solve_lambda = cases.solve_lambda.map((a) => {
  const lam = MSO.solveLambda(a[0], a[1]);
  return { lam: lam, alpha: MSO.optimalAuthority(a[0], lam) };
});
out.buffer = cases.buffer.map((a) => MSO.effectiveAutonomyBuffer(a[0], a[1], a[2], a[3]));
out.autonomy = cases.autonomy.map((a) => MSO.autonomyTime(a[0], a[1], a[2], a[3], a[4]));
out.crit_entropy = cases.crit_entropy.map((a) => MSO.criticalEntropy(a[0], a[1], a[2]));

out.pipelines = cases.pipelines.map((pc) => {
  const r = MSO.analyzePipeline(pc.pipeline, { p_min: pc.p_min, process_entropy: pc.hw });
  const masking = {};
  Object.keys(r.perNode).forEach((k) => { masking[k] = r.perNode[k].masking; });
  return { cop: r.cop, beff: r.beff, hcrit: r.hcrit, bottleneck: r.bottleneck, feasible: r.feasible, masking: masking };
});

fs.writeFileSync(outPath, JSON.stringify(out));
