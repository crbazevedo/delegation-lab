/**
 * mso-priors.js — cold-start σ_raw / catch_rate / fix_rate priors for cockpit nodes.
 *
 * GENERATED FROM src/minimal_oversight/data/priors.yaml — DO NOT EDIT BY HAND.
 * Regenerate with:  python scripts/gen_priors_js.py
 *
 * Mirrors minimal_oversight.priors.seed_node (Python) exactly:
 *   - generator / retrieval / reranking task-types → sigma_skill = clamp(mid/γ, 0.05, 0.98)
 *     so gamma * sigma_skill == band.mid at the return-operator fixed point.
 *   - review task-type → catch_rate = clamp(mid, 0, 1)   (reviewer error-detection)
 *   - correction task-type → fix_rate = clamp(mid, 0, 1)  (corrector repair-success)
 *   - provenance.confidence = 1 − band_width (a crude evidence-strength proxy).
 *
 * Provenance for every band: docs/methodology/priors-evidence.md.
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
  "gpt-4o|extraction": {kind:"generator",band:{low:0.8,mid:0.91,high:0.98},benchmark:"JSONSchemaBench",metric_kind:"absolute",note:"OpenAI JSON-mode raises compliance on accepted schemas; coverage drops on hard schemas; moderate schema default"},
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
  "deepseek-r1|drafting": {kind:"generator",band:{low:0.8,mid:0.87,high:0.91},benchmark:"Vectara-HHEM + DeepSeek blog",metric_kind:"absolute",note:"REASONING PENALTY confirmed; R1 substantially worse than V3 on faithfulness; R1-0528 narrowed gap ~45-50% \u2014 widen"},
  "qwen2.5-72b|drafting": {kind:"generator",band:{low:0.78,mid:0.85,high:0.92},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; mid tier faithfulness; wide band"},
  "mistral-large|drafting": {kind:"generator",band:{low:0.78,mid:0.85,high:0.92},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; mid tier faithfulness; wide band"},
  "claude-opus-4|grounded_generation": {kind:"generator",band:{low:0.83,mid:0.89,high:0.94},benchmark:"Vectara-HHEM + FaithBench/RAGTruth",metric_kind:"absolute",note:"faithfulness PROXY \u2014 not full RAG answer-correctness; interpolated above Sonnet anchor"},
  "claude-sonnet-4|grounded_generation": {kind:"generator",band:{low:0.8,mid:0.87,high:0.93},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"direct FaithBench measurement; faithfulness PROXY only; Sonnet-4.5 confirmed >10% hallu \u2014 use low end of band"},
  "claude-haiku-4|grounded_generation": {kind:"generator",band:{low:0.75,mid:0.83,high:0.9},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; small tier; faithfulness proxy only; refine from traces"},
  "gpt-4o|grounded_generation": {kind:"generator",band:{low:0.8,mid:0.84,high:0.9},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"direct FaithBench measurement; faithfulness PROXY only"},
  "gpt-4o-mini|grounded_generation": {kind:"generator",band:{low:0.72,mid:0.8,high:0.88},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; small tier; faithfulness proxy only"},
  "openai-o3|grounded_generation": {kind:"generator",band:{low:0.8,mid:0.87,high:0.93},benchmark:"Vectara next-gen (interpolated)",metric_kind:"relative",note:"reasoning models WORSE on faithfulness than Flash; wide band; faithfulness proxy only"},
  "gemini-2-pro|grounded_generation": {kind:"generator",band:{low:0.88,mid:0.93,high:0.97},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"best faithfulness in FaithBench set; faithfulness PROXY only; note HHEM conflict-of-interest"},
  "gemini-2-flash|grounded_generation": {kind:"generator",band:{low:0.88,mid:0.93,high:0.97},benchmark:"Vectara-HHEM + FaithBench",metric_kind:"absolute",note:"Flash-class tops HHEM; FaithBench confirms strong faithfulness; PROXY only"},
  "llama-3.3-70b|grounded_generation": {kind:"generator",band:{low:0.78,mid:0.84,high:0.9},benchmark:"FaithBench/RAGTruth",metric_kind:"absolute",note:"direct FaithBench measurement; faithfulness PROXY only; 70B tier"},
  "deepseek-v3|grounded_generation": {kind:"generator",band:{low:0.88,mid:0.93,high:0.96},benchmark:"Vectara-HHEM + DeepSeek blog",metric_kind:"absolute",note:"V3 outstanding faithfulness; faithfulness PROXY only; does not predict end-to-end RAG correctness"},
  "deepseek-r1|grounded_generation": {kind:"generator",band:{low:0.78,mid:0.86,high:0.91},benchmark:"Vectara-HHEM + DeepSeek blog",metric_kind:"absolute",note:"REASONING PENALTY on faithfulness; R1+RAG can hit 86% clinical accuracy despite poor faithfulness \u2014 proxy gap CRITICAL"},
  "qwen2.5-72b|grounded_generation": {kind:"generator",band:{low:0.75,mid:0.85,high:0.92},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; mid tier faithfulness proxy; wide band"},
  "mistral-large|grounded_generation": {kind:"generator",band:{low:0.75,mid:0.85,high:0.92},benchmark:"Vectara-HHEM (interpolated)",metric_kind:"relative",note:"interpolated; mid tier faithfulness proxy; wide band"},
  "claude-opus-4|review": {kind:"review",band:{low:0.62,mid:0.72,high:0.84},benchmark:"FaithJudge / MT-Bench (zero-shot LLM judge)",metric_kind:"absolute",note:"SOFTEST COLUMN; strong frontier judge tier; zero-shot only; few-shot raises to ~84% (not assumed here); wide band mandatory"},
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
  "mistral-large|review": {kind:"review",band:{low:0.5,mid:0.6,high:0.74},benchmark:"FaithJudge / CriticBench (no reliable evidence)",metric_kind:"relative",note:"SOFTEST COLUMN; conservative wide-band fallback per research guidance; no reliable evidence"},
  "gpt-5.4-nano|drafting": {kind:"generator",band:{low:0.9,mid:0.93,high:0.96},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"CONFIRMED top-tier faithfulness; faithfulness subdim only; style/IF quality is relative-only and NOT captured"},
  "gpt-5.4-nano|grounded_generation": {kind:"generator",band:{low:0.9,mid:0.93,high:0.96},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"RAG reader faithfulness proxy; retrieval STEP is an embedder (see retrieval task)"},
  "gemini-2.5-flash-lite|drafting": {kind:"generator",band:{low:0.9,mid:0.93,high:0.96},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"CONFIRMED top-tier faithfulness; faithfulness subdim only"},
  "gemini-2.5-flash-lite|grounded_generation": {kind:"generator",band:{low:0.9,mid:0.93,high:0.96},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"RAG reader faithfulness proxy"},
  "gemini-2.5-pro|drafting": {kind:"generator",band:{low:0.82,mid:0.89,high:0.94},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"SOURCED (verification rate-limited); faithfulness subdim only; wider band"},
  "gemini-2.5-pro|grounded_generation": {kind:"generator",band:{low:0.82,mid:0.89,high:0.94},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"RAG reader faithfulness proxy; SOURCED"},
  "phi-4|drafting": {kind:"generator",band:{low:0.89,mid:0.93,high:0.96},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"SOURCED; small-model strong faithfulness; faithfulness subdim only"},
  "phi-4|grounded_generation": {kind:"generator",band:{low:0.89,mid:0.93,high:0.96},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"RAG reader faithfulness proxy; SOURCED"},
  "qwen3-8b|drafting": {kind:"generator",band:{low:0.86,mid:0.91,high:0.95},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"SOURCED; faithfulness subdim only"},
  "qwen3-8b|grounded_generation": {kind:"generator",band:{low:0.86,mid:0.91,high:0.95},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"RAG reader faithfulness proxy; SOURCED"},
  "kimi-k2.5|drafting": {kind:"generator",band:{low:0.7,mid:0.8,high:0.88},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"SOURCED; mid-low faithfulness; faithfulness subdim only; wide band"},
  "kimi-k2.5|grounded_generation": {kind:"generator",band:{low:0.7,mid:0.8,high:0.88},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"RAG reader faithfulness proxy; SOURCED"},
  "o3-pro|drafting": {kind:"generator",band:{low:0.58,mid:0.7,high:0.82},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"CONFIRMED reasoning-vs-faithfulness penalty; a reasoning model is a WORSE drafting prior than its base sibling; wide band"},
  "o3-pro|grounded_generation": {kind:"generator",band:{low:0.58,mid:0.7,high:0.82},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"CONFIRMED reasoning penalty; reader faithfulness proxy; wide band"},
  "o4-mini-high|drafting": {kind:"generator",band:{low:0.64,mid:0.75,high:0.85},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"CONFIRMED reasoning penalty; faithfulness subdim only; wide band"},
  "o4-mini-high|grounded_generation": {kind:"generator",band:{low:0.64,mid:0.75,high:0.85},benchmark:"Vectara-HHEM-2.3",metric_kind:"absolute",note:"CONFIRMED reasoning penalty; reader faithfulness proxy; wide band"},
  "gpt-5.5|drafting": {kind:"generator",band:{low:0.86,mid:0.92,high:0.96},benchmark:"NONE (interpolated from gpt-5.4-nano)",metric_kind:"relative",note:"INTERPOLATED from gpt-5.4-nano tier; no public benchmark for this exact name; wide band; refine from traces"},
  "gpt-5.5|grounded_generation": {kind:"generator",band:{low:0.86,mid:0.92,high:0.96},benchmark:"NONE (interpolated from gpt-5.4-nano)",metric_kind:"relative",note:"INTERPOLATED; reader faithfulness proxy; no public benchmark for exact name"},
  "claude-opus-4.8|drafting": {kind:"generator",band:{low:0.78,mid:0.86,high:0.93},benchmark:"NONE (interpolated from claude-opus-4)",metric_kind:"relative",note:"INTERPOLATED from Claude Opus 4 (modest gen-over-gen lift assumed); no public benchmark for exact name; wide band"},
  "claude-opus-4.8|grounded_generation": {kind:"generator",band:{low:0.78,mid:0.86,high:0.93},benchmark:"NONE (interpolated from claude-opus-4)",metric_kind:"relative",note:"INTERPOLATED; reader faithfulness proxy; no public benchmark for exact name"},
  "kimi-2.6|drafting": {kind:"generator",band:{low:0.7,mid:0.81,high:0.89},benchmark:"NONE (interpolated from kimi-k2.5)",metric_kind:"relative",note:"INTERPOLATED from Kimi-K2.5; no public benchmark for exact name; wide band"},
  "kimi-2.6|grounded_generation": {kind:"generator",band:{low:0.7,mid:0.81,high:0.89},benchmark:"NONE (interpolated from kimi-k2.5)",metric_kind:"relative",note:"INTERPOLATED; reader faithfulness proxy; no public benchmark for exact name"},
  "fable-5|drafting": {kind:"generator",band:{low:0.65,mid:0.8,high:0.92},benchmark:"NONE (no public evidence)",metric_kind:"relative",note:"NO PUBLIC BENCHMARK FOUND; deliberately wide conservative band; this is a placeholder to refine from your own traces, not a measurement"},
  "fable-5|grounded_generation": {kind:"generator",band:{low:0.65,mid:0.8,high:0.92},benchmark:"NONE (no public evidence)",metric_kind:"relative",note:"NO PUBLIC BENCHMARK FOUND; wide conservative band; refine from traces"},
  "qwen3-embedding-8b|retrieval": {kind:"generator",band:{low:0.62,mid:0.68,high:0.74},benchmark:"MTEB-English-v2 (Retrieval)",metric_kind:"absolute",note:"retrieval \u03c3 \u2248 P(relevant in top-k); leaderboard upper-bound, corpus-dependent; SOURCED"},
  "openai-text-embedding-3-large|retrieval": {kind:"generator",band:{low:0.52,mid:0.58,high:0.64},benchmark:"BEIR / MTEB-English",metric_kind:"absolute",note:"retrieval \u03c3 from BEIR nDCG@10; corpus-dependent; SOURCED"},
  "openai-text-embedding-3-small|retrieval": {kind:"generator",band:{low:0.48,mid:0.55,high:0.62},benchmark:"MTEB-English",metric_kind:"absolute",note:"cheaper/smaller embedder; corpus-dependent; SOURCED"},
  "cohere-embed-v3|retrieval": {kind:"generator",band:{low:0.5,mid:0.57,high:0.63},benchmark:"MTEB-English",metric_kind:"absolute",note:"corpus-dependent; SOURCED"},
  "e5-mistral-7b|retrieval": {kind:"generator",band:{low:0.52,mid:0.59,high:0.65},benchmark:"MTEB-English",metric_kind:"absolute",note:"7B LLM-initialized embedder; corpus-dependent; SOURCED"},
  "bge-m3|retrieval": {kind:"generator",band:{low:0.46,mid:0.53,high:0.6},benchmark:"BEIR / MIRACL",metric_kind:"absolute",note:"strong open multilingual embedder; corpus-dependent; SOURCED"},
  "granite-embedding-r2|retrieval": {kind:"generator",band:{low:0.48,mid:0.55,high:0.62},benchmark:"BEIR / MTEB-v2 Retrieval",metric_kind:"absolute",note:"compact ModernBERT embedder; corpus-dependent; SOURCED"},
  "qwen3-reranker|reranking": {kind:"generator",band:{low:0.65,mid:0.71,high:0.76},benchmark:"MTEB-R (over Qwen3-Embedding)",metric_kind:"absolute",note:"cross-encoder; post-rerank P(correct in top-k); corpus-dependent; SOURCED"},
  "cohere-rerank-3|reranking": {kind:"generator",band:{low:0.58,mid:0.65,high:0.72},benchmark:"BEIR / TREC-DL (cross-encoder)",metric_kind:"relative",note:"cross-encoder; relative-only public evidence; wide band; SOURCED"},
  "bge-reranker-v2-m3|reranking": {kind:"generator",band:{low:0.55,mid:0.61,high:0.67},benchmark:"MTEB-R (cross-encoder)",metric_kind:"absolute",note:"open cross-encoder reranker; corpus-dependent; SOURCED"},
  "rankzephyr-7b|reranking": {kind:"generator",band:{low:0.62,mid:0.69,high:0.75},benchmark:"TREC-DL19 / FutureQueryEval (listwise LLM)",metric_kind:"absolute",note:"listwise LLM reranker (post-ranking, NOT retrieval); recency penalty on novel queries; SOURCED"},
  "rankgpt-gpt4|reranking": {kind:"generator",band:{low:0.66,mid:0.72,high:0.78},benchmark:"TREC-DL19 (listwise LLM)",metric_kind:"absolute",note:"listwise LLM post-ranking; an LLM's legitimate role in retrieval is reranking, NOT the retrieval step; SOURCED"},
  "llm-judge-single|review": {kind:"review",band:{low:0.6,mid:0.68,high:0.74},benchmark:"RewardBench-2 (single LLM judge, k=1)",metric_kind:"absolute",note:"a single LLM-as-judge call; SOFTEST COLUMN; subject to position/verbosity/self-preference bias; SOURCED"},
  "llm-judge-ensemble|review": {kind:"review",band:{low:0.72,mid:0.8,high:0.85},benchmark:"RewardBench-2 (ensemble k=8)",metric_kind:"absolute",note:"ensembling N independent judge calls materially raises catch_rate (+~10pp); still bias-prone; SOURCED"},
  "human-reviewer|review": {kind:"review",band:{low:0.75,mid:0.85,high:0.92},benchmark:"paper assumption (domain-expert reviewer)",metric_kind:"relative",note:"human domain expert; higher catch than a single LLM judge but slower/costly; for code, a strong LLM judge can rival humans; refine from traces"},
  "corrector-no-feedback|correction": {kind:"correction",band:{low:0.1,mid:0.3,high:0.55},benchmark:"LLMs Cannot Self-Correct Reasoning Yet",metric_kind:"absolute",note:"corrector with NO reviewer feedback; unreliable \u2192 low/wide band; this is why detection (reviewer) and repair (corrector) must be modeled separately"},
  "corrector-with-feedback|correction": {kind:"correction",band:{low:0.55,mid:0.7,high:0.85},benchmark:"When Can LLMs Actually Correct Their Own Mistakes (TACL 2024)",metric_kind:"absolute",note:"corrector that CONSUMES reviewer feedback and re-does/patches; fix_rate is high only when the feedback signal is reliable; SOURCED"},
  "corrector-with-oracle|correction": {kind:"correction",band:{low:0.65,mid:0.78,high:0.9},benchmark:"Reflexion / agentic re-do with test or oracle signal",metric_kind:"absolute",note:"corrector with a verifiable signal (tests, exec results); highest fix_rate; degrades if the signal is noisy; SOURCED"},
  };

  var MODELS = ["bge-m3", "bge-reranker-v2-m3", "claude-haiku-4", "claude-opus-4", "claude-opus-4.8", "claude-sonnet-4", "cohere-embed-v3", "cohere-rerank-3", "corrector-no-feedback", "corrector-with-feedback", "corrector-with-oracle", "deepseek-r1", "deepseek-v3", "e5-mistral-7b", "fable-5", "gemini-2-flash", "gemini-2-pro", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gpt-4o", "gpt-4o-mini", "gpt-5.4-nano", "gpt-5.5", "granite-embedding-r2", "human-reviewer", "kimi-2.6", "kimi-k2.5", "llama-3.3-70b", "llm-judge-ensemble", "llm-judge-single", "mistral-large", "o3-pro", "o4-mini-high", "openai-o3", "openai-text-embedding-3-large", "openai-text-embedding-3-small", "phi-4", "qwen2.5-72b", "qwen3-8b", "qwen3-embedding-8b", "qwen3-reranker", "rankgpt-gpt4", "rankzephyr-7b"];
  var TASK_TYPES = ["code_generation", "classification", "extraction", "drafting", "grounded_generation", "retrieval", "reranking", "review", "correction"];

  // ---- public API ------------------------------------------------------------

  /** List all model names in the table. */
  function listModels() { return MODELS.slice(); }

  /** List all task-type names in the table. */
  function listTaskTypes() { return TASK_TYPES.slice(); }

  /** List the task-types that have a prior for the given model. */
  function tasksForModel(model) {
    return TASK_TYPES.filter(function (t) { return !!CELLS[model + "|" + t]; });
  }

  /** List the models that have a prior for the given task-type. */
  function modelsForTask(taskType) {
    return MODELS.filter(function (m) { return !!CELLS[m + "|" + taskType]; });
  }

  /** Return true if a prior exists for the (model, taskType) pair. */
  function hasCell(model, taskType) { return !!(CELLS[model + "|" + taskType]); }

  /**
   * Seed a cockpit Node from a (model, taskType) prior.
   *
   * Returns an object ready to be merged onto a node:
   *   { model, task_type, is_prior: true, seeds, sigma_skill?, catch_rate?, fix_rate?, provenance }
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
    } else if (taskType === "correction") {
      out.fix_rate = clamp(b.mid, 0, 1);
      out.seeds = "fix_rate";
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

  /** The prior band MID for (model, task), or null. Used by the optimizer. */
  function priorMid(model, taskType) {
    var cell = CELLS[model + "|" + taskType];
    return cell ? cell.band.mid : null;
  }

  return {
    listModels: listModels, listTaskTypes: listTaskTypes,
    tasksForModel: tasksForModel, modelsForTask: modelsForTask,
    hasCell: hasCell, seedNode: seedNode, priorMid: priorMid, GAMMA: GAMMA
  };
});
