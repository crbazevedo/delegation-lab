/**
 * mso-priors.js — cold-start σ_raw/catch_rate priors for MSO cockpit nodes.
 *
 * Mirrors minimal_oversight.priors.seed_node (Python) exactly:
 *   - generator task-types → sigma_skill = clamp(band.mid / γ, 0.05, 0.98)
 *     so gamma * sigma_skill == band.mid at the fixed point.
 *   - review task-type → catch_rate = clamp(band.mid, 0, 1)
 *   - provenance.confidence = 1 − band_width (a crude evidence-strength proxy)
 *
 * Data sourced from a cited deep-research pass (2026-06-17) against:
 *   - LiveBench Coding (code_generation, absolute)
 *   - JSONSchemaBench arXiv:2501.10868 (extraction, absolute)
 *   - Vectara HHEM-2.3 + FaithBench/RAGTruth (drafting + retrieval, absolute)
 *   - FaithJudge / MT-Bench / RewardBench-2 / CriticBench (review, absolute/relative)
 *   - Conservative tier-interpolation (classification — no surviving absolute benchmark)
 *
 * Parity: tests/test_parity.py pins JS ↔ Python to within 1e-9 on seedNode outputs.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.MSO_Priors = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var GAMMA = 10 / 12;   // η/(η+δ) return-operator fixed-point gain

  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }

  // ---- bundled prior table (generated from data/priors.yaml) -----------------
  var CELLS = {
  "claude-opus-4|code_generation": {kind:"generator",band:{low:0.62,mid:0.74,high:0.86},benchmark:"LiveBench-Coding",metric_kind:"absolute",note:"interpolated above claude-3.5-sonnet 63.2 via relative leaderboard; 10% domain-shift discount; wide band"},
  "claude-sonnet-4|code_generation": {kind:"generator",band:{low:0.58,mid:0.7,high:0.83},benchmark:"LiveBench-Coding",metric_kind:"absolute",note:"anchored to claude-3.5-sonnet 63.2; 10% domain-shift discount; Sonnet-4 interpolated near that anchor"},
  "claude-haiku-4|code_generation": {kind:"generator",band:{low:0.3,mid:0.45,high:0.62},benchmark:"LiveBench-Coding",metric_kind:"absolute",note:"anchored claude-3-haiku 24.5; HumanEval 75.9 inflates vs SWE-bench ~23%; wide band captures both"},
  "gpt-4o|code_generation": {kind:"generator",band:{low:0.4,mid:0.5,high:0.62},benchmark:"LiveBench-Coding",metric_kind:"absolute",note:"direct read from Table 1; 10% domain-shift discount; model may have since improved"},
  "gpt-4o-mini|code_generation": {kind:"generator",band:{low:0.32,mid:0.46,high:0.62},benchmark:"LiveBench-Coding + HumanEval cross-check",metric_kind:"absolute",note:"HumanEval 87.2 inflates vs SWE-bench-Verified ~23%; mid splits the difference; wide band"},
  "openai-o3|code_generation": {kind:"generator",band:{low:0.55,mid:0.68,high:0.84},benchmark:"LiveBench-Coding (interpolated)",metric_kind:"relative",note:"relative-only interpolation; reasoning models excel on coding; wide band mandatory"},
  "gemini-2-pro|code_generation": {kind:"generator",band:{low:0.45,mid:0.58,high:0.74},benchmark:"LiveBench-Coding",metric_kind:"absolute",note:"interpolated above gemini-1.5-pro 32.8; Gemini 2.x generation boost assumed modest"},
  "gemini-2-flash|code_generation": {kind:"generator",band:{low:0.35,mid:0.48,high:0.62},benchmark:"LiveBench-Coding",metric_kind:"absolute",note:"anchored to gemini-1.5-flash 39.1; 2.0/2.5 Flash improvements likely push mid up; widen"},
  "llama-3.3-70b|code_generation": {kind:"generator",band:{low:0.35,mid:0.48,high:0.62},benchmark:"LiveBench-Coding (interpolated)",metric_kind:"relative",note:"relative-only interpolation from model-class ranking; wide band"},
  "deepseek-v3|code_generation": {kind:"generator",band:{low:0.42,mid:0.55,high:0.7},benchmark:"LiveBench-Coding",metric_kind:"absolute",note:"anchored deepseek-coder-v2 41.1; V3 and R1 interpolated up; coding-focused model widens high end"},
  "deepseek-r1|code_generation": {kind:"generator",band:{low:0.48,mid:0.62,high:0.78},benchmark:"LiveBench-Coding (interpolated)",metric_kind:"relative",note:"R1 reasoning premium likely lifts coding above V3 base; no clean 2025 absolute snapshot"},
  "qwen2.5-72b|code_generation": {kind:"generator",band:{low:0.32,mid:0.45,high:0.6},benchmark:"LiveBench-Coding",metric_kind:"absolute",note:"anchored qwen2-72b 31.8; Qwen2.5 improvements likely push mid up modestly"},
  "mistral-large|code_generation": {kind:"generator",band:{low:0.32,mid:0.45,high:0.6},benchmark:"LiveBench-Coding (interpolated)",metric_kind:"relative",note:"relative-only interpolation; no direct LiveBench measurement found"},
  "claude-opus-4|classification": {kind:"generator",band:{low:0.85,mid:0.92,high:0.97},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; frontier tier conservative interpolation; refine immediately"},
  "claude-sonnet-4|classification": {kind:"generator",band:{low:0.78,mid:0.87,high:0.94},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; mid tier conservative interpolation; refine immediately"},
  "claude-haiku-4|classification": {kind:"generator",band:{low:0.7,mid:0.82,high:0.92},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; small tier conservative interpolation; refine immediately"},
  "gpt-4o|classification": {kind:"generator",band:{low:0.78,mid:0.87,high:0.94},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"MMLU vendor proxy refuted; mid tier conservative interpolation; wide band"},
  "gpt-4o-mini|classification": {kind:"generator",band:{low:0.7,mid:0.82,high:0.92},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"MMLU vendor proxy refuted; small tier conservative interpolation"},
  "openai-o3|classification": {kind:"generator",band:{low:0.85,mid:0.92,high:0.97},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"reasoning premium assumed; frontier tier conservative interpolation; refine immediately"},
  "gemini-2-pro|classification": {kind:"generator",band:{low:0.78,mid:0.87,high:0.94},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; mid tier conservative interpolation"},
  "gemini-2-flash|classification": {kind:"generator",band:{low:0.75,mid:0.85,high:0.93},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; mid tier conservative interpolation"},
  "llama-3.3-70b|classification": {kind:"generator",band:{low:0.75,mid:0.85,high:0.93},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; mid tier conservative interpolation"},
  "deepseek-v3|classification": {kind:"generator",band:{low:0.78,mid:0.87,high:0.94},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; mid tier conservative interpolation"},
  "deepseek-r1|classification": {kind:"generator",band:{low:0.78,mid:0.87,high:0.94},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; mid tier; reasoning premium unclear for classification"},
  "qwen2.5-72b|classification": {kind:"generator",band:{low:0.75,mid:0.85,high:0.93},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; mid tier conservative interpolation"},
  "mistral-large|classification": {kind:"generator",band:{low:0.75,mid:0.85,high:0.93},benchmark:"NONE (conservative interpolation)",metric_kind:"relative",note:"NO absolute benchmark survived verification; mid tier conservative interpolation"},
  "claude-opus-4|extraction": {kind:"generator",band:{low:0.82,mid:0.91,high:0.98},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"moderate schema, plain prompting; frontier tier; schema difficulty dominates; wide band"},
  "claude-sonnet-4|extraction": {kind:"generator",band:{low:0.75,mid:0.87,high:0.96},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"moderate schema, plain prompting; mid tier; wide band to capture difficulty variance"},
  "claude-haiku-4|extraction": {kind:"generator",band:{low:0.5,mid:0.7,high:0.88},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"small/efficient tier; Llama-1B floor; Haiku expected above floor but degrades on hard schemas"},
  "gpt-4o|extraction": {kind:"generator",band:{low:0.8,mid:0.91,high:0.98},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"OpenAI JSON-mode raises compliance on accepted schemas; coverage drops on hard schemas; moderate schema"},
  "gpt-4o-mini|extraction": {kind:"generator",band:{low:0.65,mid:0.8,high:0.93},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"smaller model; JSON-mode available but coverage limited; wide band"},
  "openai-o3|extraction": {kind:"generator",band:{low:0.82,mid:0.92,high:0.99},benchmark:"JSONSchemaBench (interpolated)",metric_kind:"absolute",note:"frontier reasoning model; constrained API expected; interpolated upward; wide band"},
  "gemini-2-pro|extraction": {kind:"generator",band:{low:0.8,mid:0.91,high:0.98},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"Gemini constrained-mode matches OpenAI on accepted schemas; coverage limited on hard schemas"},
  "gemini-2-flash|extraction": {kind:"generator",band:{low:0.72,mid:0.85,high:0.95},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"mid tier; constrained output may vary; moderate schema assumed"},
  "llama-3.3-70b|extraction": {kind:"generator",band:{low:0.65,mid:0.8,high:0.93},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"mid tier open model; plain prompting assumed; degrades on hard schemas"},
  "deepseek-v3|extraction": {kind:"generator",band:{low:0.72,mid:0.85,high:0.95},benchmark:"JSONSchemaBench (interpolated)",metric_kind:"absolute",note:"interpolated mid-to-frontier tier; V3 strong at structured output"},
  "deepseek-r1|extraction": {kind:"generator",band:{low:0.65,mid:0.8,high:0.93},benchmark:"JSONSchemaBench (interpolated)",metric_kind:"relative",note:"reasoning overhead may reduce extraction accuracy; conservative mid-tier interpolation"},
  "qwen2.5-72b|extraction": {kind:"generator",band:{low:0.65,mid:0.8,high:0.93},benchmark:"JSONSchemaBench (interpolated)",metric_kind:"absolute",note:"mid tier; Qwen2.5 strong at structured output but no direct JSONSchemaBench row"},
  "mistral-large|extraction": {kind:"generator",band:{low:0.65,mid:0.8,high:0.93},benchmark:"JSONSchemaBench (interpolated)",metric_kind:"relative",note:"relative-only interpolation; mid tier; wide band"},
  "claude-opus-4|drafting": {kind:"generator",band:{low:0.83,mid:0.89,high:0.95},benchmark:"Vectara-HHEM + FaithBench/RAGTruth (faithfulness subdim)",metric_kind:"absolute",note:"faithfulness subdim ONLY; style/IF quality is relative-only (AlpacaEval/Arena) and NOT captured here"},
  "claude-sonnet-4|drafting": {kind:"generator",band:{low:0.8,mid:0.87,high:0.93},benchmark:"Vectara-HHEM + FaithBench/RAGTruth",metric_kind:"absolute",note:"Sonnet-4.5 >10% hallucination rate per Vectara next-gen; faithfulness subdim only"},
  "claude-haiku-4|drafting": {kind:"generator",band:{low:0.75,mid:0.83,high:0.91},benchmark:"Vectara-HHEM (faithfulness proxy, interpolated)",metric_kind:"relative",note:"interpolated below Sonnet faithfulness; faithfulness subdim only; style quality relative-only"},
  "gpt-4o|drafting": {kind:"generator",band:{low:0.78,mid:0.85,high:0.91},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"direct FaithBench measurement; faithfulness subdim only; style relative-only"},
  "gpt-4o-mini|drafting": {kind:"generator",band:{low:0.72,mid:0.81,high:0.9},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated small-tier; faithfulness subdim only; refine quickly"},
  "openai-o3|drafting": {kind:"generator",band:{low:0.8,mid:0.88,high:0.94},benchmark:"Vectara next-gen (interpolated)",metric_kind:"relative",note:"reasoning flagships WORSE than Flash on faithfulness; faithfulness subdim only"},
  "gemini-2-pro|drafting": {kind:"generator",band:{low:0.87,mid:0.93,high:0.97},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"best-in-class faithfulness per FaithBench; faithfulness subdim only; style quality relative-only"},
  "gemini-2-flash|drafting": {kind:"generator",band:{low:0.88,mid:0.93,high:0.97},benchmark:"Vectara-HHEM",metric_kind:"absolute",note:"Flash-class tops HHEM faithfulness leaderboard; faithfulness subdim only; note HHEM is Vectara's own judge"},
  "llama-3.3-70b|drafting": {kind:"generator",band:{low:0.78,mid:0.84,high:0.9},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"direct FaithBench measurement; faithfulness subdim only; style relative-only"},
  "deepseek-v3|drafting": {kind:"generator",band:{low:0.88,mid:0.93,high:0.97},benchmark:"Vectara-HHEM + DeepSeek blog",metric_kind:"absolute",note:"V3 is notably less hallucinatory than R1; one of the best base-model faithfulness rates"},
  "deepseek-r1|drafting": {kind:"generator",band:{low:0.8,mid:0.87,high:0.91},benchmark:"Vectara-HHEM + DeepSeek blog",metric_kind:"absolute",note:"REASONING PENALTY confirmed; R1 substantially worse than V3 on faithfulness; R1-0528 narrowed gap ~45-50%"},
  "qwen2.5-72b|drafting": {kind:"generator",band:{low:0.78,mid:0.85,high:0.92},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; mid tier faithfulness; wide band"},
  "mistral-large|drafting": {kind:"generator",band:{low:0.78,mid:0.85,high:0.92},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; mid tier faithfulness; wide band"},
  "claude-opus-4|retrieval": {kind:"generator",band:{low:0.83,mid:0.89,high:0.94},benchmark:"Vectara-HHEM + FaithBench/RAGTruth",metric_kind:"absolute",note:"faithfulness PROXY — not full RAG answer-correctness; interpolated above Sonnet anchor"},
  "claude-sonnet-4|retrieval": {kind:"generator",band:{low:0.8,mid:0.87,high:0.93},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"direct FaithBench measurement; faithfulness PROXY only; Sonnet-4.5 confirmed >10% hallu — use low end"},
  "claude-haiku-4|retrieval": {kind:"generator",band:{low:0.75,mid:0.83,high:0.9},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; small tier; faithfulness proxy only; refine from traces"},
  "gpt-4o|retrieval": {kind:"generator",band:{low:0.8,mid:0.84,high:0.9},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"direct FaithBench measurement; faithfulness PROXY only"},
  "gpt-4o-mini|retrieval": {kind:"generator",band:{low:0.72,mid:0.8,high:0.88},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; small tier; faithfulness proxy only"},
  "openai-o3|retrieval": {kind:"generator",band:{low:0.8,mid:0.87,high:0.93},benchmark:"Vectara next-gen (interpolated)",metric_kind:"relative",note:"reasoning models WORSE on faithfulness than Flash; wide band; faithfulness proxy only"},
  "gemini-2-pro|retrieval": {kind:"generator",band:{low:0.88,mid:0.93,high:0.97},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"best faithfulness in FaithBench set; faithfulness PROXY only; note HHEM conflict-of-interest"},
  "gemini-2-flash|retrieval": {kind:"generator",band:{low:0.88,mid:0.93,high:0.97},benchmark:"Vectara-HHEM + FaithBench",metric_kind:"absolute",note:"Flash-class tops HHEM; FaithBench confirms strong faithfulness; PROXY only"},
  "llama-3.3-70b|retrieval": {kind:"generator",band:{low:0.78,mid:0.84,high:0.9},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"direct FaithBench measurement; faithfulness PROXY only; 70B tier"},
  "deepseek-v3|retrieval": {kind:"generator",band:{low:0.88,mid:0.93,high:0.96},benchmark:"Vectara-HHEM + DeepSeek blog",metric_kind:"absolute",note:"V3 outstanding faithfulness; faithfulness PROXY only; does not predict end-to-end RAG correctness"},
  "deepseek-r1|retrieval": {kind:"generator",band:{low:0.78,mid:0.86,high:0.91},benchmark:"Vectara-HHEM + DeepSeek blog",metric_kind:"absolute",note:"REASONING PENALTY on faithfulness; R1+RAG can hit 86% clinical accuracy despite poor faithfulness — proxy gap CRITICAL"},
  "qwen2.5-72b|retrieval": {kind:"generator",band:{low:0.75,mid:0.85,high:0.92},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; mid tier faithfulness proxy; wide band"},
  "mistral-large|retrieval": {kind:"generator",band:{low:0.75,mid:0.85,high:0.92},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; mid tier faithfulness proxy; wide band"},
  "claude-opus-4|review": {kind:"review",band:{low:0.62,mid:0.72,high:0.84},benchmark:"FaithJudge / MT-Bench (zero-shot LLM judge)",metric_kind:"absolute",note:"SOFTEST COLUMN; strong frontier judge tier; zero-shot only; few-shot raises to ~84% (not assumed here); wide band"},
  "claude-sonnet-4|review": {kind:"review",band:{low:0.55,mid:0.65,high:0.78},benchmark:"FaithJudge / MT-Bench (zero-shot LLM judge)",metric_kind:"absolute",note:"SOFTEST COLUMN; mid judge tier; zero-shot only; RewardBench-2 shows ~20pp drop on harder distributions; wide band"},
  "claude-haiku-4|review": {kind:"review",band:{low:0.48,mid:0.58,high:0.7},benchmark:"FaithJudge / MT-Bench (zero-shot LLM judge)",metric_kind:"absolute",note:"SOFTEST COLUMN; small judge tier; near-random on hard distributions; wide band; do not use as sole quality gate"},
  "gpt-4o|review": {kind:"review",band:{low:0.55,mid:0.65,high:0.78},benchmark:"MT-Bench + FaithJudge",metric_kind:"absolute",note:"pairwise preference easier than absolute error-catch; MT-Bench bias documented (position/verbosity/self-enhancement); mid judge tier"},
  "gpt-4o-mini|review": {kind:"review",band:{low:0.48,mid:0.58,high:0.7},benchmark:"FaithJudge (zero-shot)",metric_kind:"absolute",note:"SOFTEST COLUMN; small judge tier; wide band; do not use as sole quality gate"},
  "openai-o3|review": {kind:"review",band:{low:0.62,mid:0.72,high:0.84},benchmark:"FaithJudge (o3-mini-high zero-shot anchor)",metric_kind:"absolute",note:"SOFTEST COLUMN; best public zero-shot judge evidence; o3-mini-high is the anchor; strong frontier judge tier"},
  "gemini-2-pro|review": {kind:"review",band:{low:0.55,mid:0.65,high:0.78},benchmark:"FaithJudge (interpolated)",metric_kind:"relative",note:"SOFTEST COLUMN; interpolated; no direct zero-shot catch-rate row for Gemini-2-Pro; mid-to-frontier tier"},
  "gemini-2-flash|review": {kind:"review",band:{low:0.52,mid:0.62,high:0.75},benchmark:"FaithJudge (interpolated)",metric_kind:"relative",note:"SOFTEST COLUMN; interpolated; mid judge tier; wide band"},
  "llama-3.3-70b|review": {kind:"review",band:{low:0.5,mid:0.62,high:0.75},benchmark:"FaithJudge / CriticBench (interpolated)",metric_kind:"relative",note:"SOFTEST COLUMN; conservative wide band fallback; no reliable evidence; refine from traces immediately"},
  "deepseek-v3|review": {kind:"review",band:{low:0.52,mid:0.63,high:0.76},benchmark:"FaithJudge (interpolated)",metric_kind:"relative",note:"SOFTEST COLUMN; interpolated; mid tier; CriticBench pairing asymmetry applies"},
  "deepseek-r1|review": {kind:"review",band:{low:0.5,mid:0.62,high:0.76},benchmark:"FaithJudge (interpolated)",metric_kind:"relative",note:"SOFTEST COLUMN; reasoning overhead uncertain for critique; conservative mid tier; wide band"},
  "qwen2.5-72b|review": {kind:"review",band:{low:0.5,mid:0.6,high:0.74},benchmark:"FaithJudge / CriticBench (no reliable evidence)",metric_kind:"relative",note:"SOFTEST COLUMN; conservative wide-band fallback per research guidance; no reliable evidence"},
  "mistral-large|review": {kind:"review",band:{low:0.5,mid:0.6,high:0.74},benchmark:"FaithJudge / CriticBench (no reliable evidence)",metric_kind:"relative",note:"SOFTEST COLUMN; conservative wide-band fallback per research guidance; no reliable evidence"}
  };

  var MODELS = ["claude-haiku-4","claude-opus-4","claude-sonnet-4","deepseek-r1","deepseek-v3","gemini-2-flash","gemini-2-pro","gpt-4o","gpt-4o-mini","llama-3.3-70b","mistral-large","openai-o3","qwen2.5-72b"];
  var TASK_TYPES = ["code_generation","classification","extraction","drafting","retrieval","review"];

  // ---- public API ------------------------------------------------------------

  /** List all model names in the table. */
  function listModels() { return MODELS.slice(); }

  /** List all task-type names in the table. */
  function listTaskTypes() { return TASK_TYPES.slice(); }

  /** Return true if a prior exists for the (model, taskType) pair. */
  function hasCell(model, taskType) { return !!(CELLS[model + "|" + taskType]); }

  /**
   * Seed a cockpit Node from a (model, taskType) prior.
   *
   * Returns an object ready to be merged onto a node:
   *   { model, task_type, is_prior: true, seeds, sigma_skill?, catch_rate, provenance }
   *
   * Mirrors Python priors.seed_node exactly. Throws if no cell exists.
   */
  function seedNode(model, taskType) {
    var cell = CELLS[model + "|" + taskType];
    if (!cell) throw new Error("no prior for model=" + model + " task_type=" + taskType);

    var b = cell.band;
    var out = { model: model, task_type: taskType, is_prior: true };

    if (taskType === "review") {
      out.catch_rate = clamp(b.mid, 0, 1);
      out.seeds = "catch_rate";
    } else {
      out.sigma_skill = clamp(b.mid / GAMMA, 0.05, 0.98);
      out.catch_rate = 0.0;
      out.seeds = "sigma_skill";
    }

    out.provenance = {
      band: { low: b.low, mid: b.mid, high: b.high },
      confidence: Math.round((1 - (b.high - b.low)) * 1000) / 1000,
      benchmark: cell.benchmark,
      metric_kind: cell.metric_kind,
      note: cell.note
    };
    return out;
  }

  return { listModels: listModels, listTaskTypes: listTaskTypes, hasCell: hasCell, seedNode: seedNode, GAMMA: GAMMA };
});
