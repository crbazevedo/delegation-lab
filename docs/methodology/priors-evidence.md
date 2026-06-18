# Priors Evidence Ledger

This page is the **provenance ledger** for the cold-start priors in
`minimal_oversight/data/priors.yaml`. Every σ band the cockpit seeds a node
with traces back to a row here. Priors are *starting points to refine with your
own traces* — not ground truth. See [Methodology](priors.md) for how raw
benchmark numbers become σ.

**Confidence tags.** Each row is tagged by how it was verified:

- **CONFIRMED** — independently corroborated (≥2 adversarial verifier votes).
- **SOURCED** — drawn from a primary leaderboard / benchmark paper, but the
  automated cross-verification pass was rate-limited before it could vote.
  Treated as cited-but-unverified → **wider bands**.
- **INTERPOLATED** — no direct public benchmark for that exact (model × task);
  a conservative wide band set by tier interpolation, flagged in-cell.

Last research sweep: **2026-06-18** (5 angles, 26 sources, 121 raw claims).

---

## Normalization rules (applied to every cell)

- **Absolute metrics** (pass@1, accuracy, F1, nDCG@10, faithfulness rate,
  judge↔human agreement) ≈ success probability → mapped to σ with a modest
  domain-shift discount (leaderboard conditions are friendlier than production).
- **Relative metrics** (Arena Elo, win-rates, preference rates) are **rankings,
  not probabilities** — never inverted into σ. Used only to *order* models that
  lack an absolute number, anchored to the scale set by absolute benchmarks.
- **Bands widen** when evidence is relative, stale, contaminated, or
  verification-limited. Retrieval σ is corpus-dependent; judge catch-rate is the
  softest column; self-correction *without external feedback* is unreliable.

---

## GAP 1 — Frontier-model faithfulness (drafting / retrieval)

Source: **Vectara HHEM-2.3 hallucination leaderboard** — summarization
factual-consistency over 7,700+ articles, temperature 0, "use only the passage."
Factual-consistency = 100% − hallucination rate. Explicitly RAG/agentic-relevant.
Updated 2026-05-11.
<https://github.com/vectara/hallucination-leaderboard> ·
<https://huggingface.co/spaces/vectara/leaderboard>

| Model | Hallucination % | Faithfulness σ (drafting/RAG) | Confidence |
|---|---|---|---|
| GPT-5.4-nano (2026-03-17) | 3.1% | 0.90 / 0.93 / 0.96 | CONFIRMED |
| Gemini-2.5-flash-lite | 3.3% | 0.90 / 0.93 / 0.96 | CONFIRMED |
| Phi-4 | 3.7% | 0.89 / 0.93 / 0.96 | SOURCED |
| Llama-3.3-70B-Instruct-Turbo | 4.1% | 0.88 / 0.92 / 0.96 | CONFIRMED |
| Qwen3-8B | 4.8% | 0.86 / 0.91 / 0.95 | SOURCED |
| GPT-4.1 | 5.6% | 0.85 / 0.90 / 0.94 | SOURCED |
| DeepSeek-V3 | 6.1% | 0.84 / 0.90 / 0.94 | CONFIRMED |
| DeepSeek-V3.2 | 6.3% | 0.84 / 0.90 / 0.94 | CONFIRMED |
| Gemini-2.5-pro | 7.0% | 0.82 / 0.89 / 0.94 | SOURCED |
| Claude Sonnet 4 | 10.3% | 0.78 / 0.86 / 0.92 | SOURCED |
| DeepSeek-R1 (reasoning) | 11.3% | 0.74 / 0.83 / 0.90 | CONFIRMED |
| Claude Opus 4 | 12.0% | 0.74 / 0.82 / 0.89 | SOURCED |
| Kimi-K2.5 | 14.2% | 0.70 / 0.80 / 0.88 | SOURCED |
| o4-Mini-High (reasoning) | 18.6% | 0.64 / 0.75 / 0.85 | CONFIRMED |
| o3-Pro (reasoning) | 23.3% | 0.58 / 0.70 / 0.82 | CONFIRMED |

**Reasoning-vs-faithfulness tradeoff (CONFIRMED 3-0).** Reasoning variants
hallucinate ~2× their non-reasoning siblings (R1 11.3% vs V3 6.1%). A reasoning
model is a *worse* drafting/RAG faithfulness prior than its base sibling — model
the reasoning variant with a lower faithfulness σ even when it is "smarter."

**Not found / no public benchmark.** No "Claude Fable" model and no exact
"GPT-5.5 / Opus 4.8 / Kimi 2.6" appears on a public faithfulness leaderboard as
of this sweep. Those names, if used in the cockpit, are **INTERPOLATED** from
the nearest benchmarked sibling and flagged in-cell — never invented numbers.

---

## GAP 2 — Embedding / retrieval models (NOT LLMs)

Retrieval is **embedding + vector search**, not an LLM generating text. The σ
here is "P(relevant item retrieved in top-k)", anchored to MTEB-v2 Retrieval /
BEIR nDCG@10. Leaderboard numbers are upper-bound-ish and **corpus-dependent** —
bands are wide. All SOURCED (verification rate-limited).

| Embedder | Anchor | Retrieval σ | Source |
|---|---|---|---|
| Qwen3-Embedding-8B | MTEB-En v2 75.2; Retrieval 70.9 | 0.62 / 0.68 / 0.74 | arXiv:2506.05176 |
| Qwen3-Embedding-4B | MTEB-En v2 74.6 | 0.60 / 0.66 / 0.72 | arXiv:2506.05176 |
| Qwen3-Embedding-0.6B | MTEB-En v2 70.7 | 0.55 / 0.62 / 0.68 | arXiv:2506.05176 |
| OpenAI text-embedding-3-large | BEIR nDCG@10 55.4; MTEB-En 64.6 | 0.52 / 0.58 / 0.64 | arXiv:2407.19669 |
| OpenAI text-embedding-3-small | MTEB-En 62.3 | 0.48 / 0.55 / 0.62 | arXiv:2407.19669 |
| Cohere Embed v3 (multilingual) | MTEB-En 64.0 | 0.50 / 0.57 / 0.63 | arXiv:2407.19669 |
| E5-mistral-7b | MTEB-En 66.6 | 0.52 / 0.59 / 0.65 | arXiv:2407.19669 |
| BGE-M3 (dense) | BEIR 48.7; MIRACL 67.7 | 0.46 / 0.53 / 0.60 | arXiv:2407.19669 |
| mGTE-TRM (dense, 304M) | BEIR 51.1; MIRACL 62.1 | 0.47 / 0.54 / 0.61 | arXiv:2407.19669 |
| granite-embedding-english-r2 (149M) | BEIR 53.1; MTEB-v2 Ret. 56.4 | 0.48 / 0.55 / 0.62 | arXiv:2508.21085 |
| granite-embedding-small-r2 (47M) | BEIR 50.9 | 0.45 / 0.52 / 0.59 | arXiv:2508.21085 |

Relative-only ordering (NOT invertible to σ): Qwen3-Embedding-8B > Gemini-Embedding
(70.6 vs 68.4 MTEB multilingual); NV-Embed-v2 56.3, GritLM-7B 60.9, gte-Qwen2-7B 62.5 trail.

---

## GAP 3 — Rerankers (post-ranking)

A reranker has **no standalone σ_raw** — it transforms a candidate list. We
record a *ranking-quality uplift* and a post-rerank "P(correct item in top-k)".
Two families: **cross-encoders** (pointwise) and **listwise LLM rerankers**.

| Reranker | Family | Uplift (nDCG@10 / MTEB-R) | Post-rerank σ | Source |
|---|---|---|---|---|
| Qwen3-Reranker (4B/8B) | cross-encoder | MTEB-R 61.8 → ~69 (+7) | 0.65 / 0.71 / 0.76 | arXiv:2506.05176 |
| Qwen3-Reranker-0.6B | cross-encoder | MTEB-R 61.8 → 65.8 (+4) | 0.62 / 0.68 / 0.73 | arXiv:2506.05176 |
| granite-reranker-r2 (149M) | cross-encoder | BEIR 53.1 → 55.4 (+2.3) | 0.55 / 0.62 / 0.68 | arXiv:2508.21085 |
| BGE-reranker-v2-m3 | cross-encoder | (MTEB-R 57.0 baseline) | 0.55 / 0.61 / 0.67 | arXiv:2506.05176 |
| Jina-reranker-v2-multilingual | cross-encoder | (MTEB-R 58.2) | 0.55 / 0.61 / 0.67 | arXiv:2506.05176 |
| RankGPT (GPT-4, listwise) | LLM listwise | TREC-DL19 75.6 nDCG@10 | 0.66 / 0.72 / 0.78 | arXiv:2508.16757 |
| RankZephyr-7B (listwise) | LLM listwise | TREC-DL19 74.2; novel 62.7 | 0.62 / 0.69 / 0.75 | arXiv:2508.16757 |
| MonoT5-3B | cross-encoder | TREC-DL19 71.8; novel 60.8 | 0.60 / 0.67 / 0.73 | arXiv:2508.16757 |

**Recency penalty (SOURCED).** On FutureQueryEval (post-April-2025 novel
queries) reranker nDCG@10 drops 5–15% vs standard benchmarks — leaderboard
numbers are optimistic; production bands should sit at the low end.

---

## GAP 4 — Reviewers (LLM-as-judge) and correctors (fix-success)

These are **two distinct roles**, and the cockpit now models them as such
(detection × fix-success, see [Methodology](priors.md)).

### (a) Reviewer catch_rate (softest column)

LLM-as-judge agreement with human preference. Source: RewardBench-2
(arXiv:2604.13717), CriticGPT (arXiv:2407.00215), MT-Bench (arXiv:2306.05685).

| Reviewer setup | Anchor | catch_rate σ | Source |
|---|---|---|---|
| Single LLM judge (k=1) | RewardBench-2 71.7% acc (N=1729) | 0.60 / 0.68 / 0.74 | arXiv:2604.13717 |
| Ensemble judge (k=8) | RewardBench-2 81.5% (+9.8pp) | 0.72 / 0.80 / 0.85 | arXiv:2604.13717 |
| Ensemble + scoring criteria | RewardBench-2 83.6% | 0.74 / 0.82 / 0.87 | arXiv:2604.13717 |
| CriticGPT (code review) | 63% preferred over human critiques | 0.55 / 0.65 / 0.75 | arXiv:2407.00215 |
| Human reviewer (domain expert) | — (paper assumption) | 0.75 / 0.85 / 0.92 | model card default |

CriticGPT's "63% preferred" is a **relative win-rate over humans**, NOT an
absolute catch fraction — used as ranking evidence only (catch_rate is mid-high
for code-error detection), never inverted to σ.

### (b) Corrector fix_rate

P(repair succeeds | error was flagged). Source: "LLMs Cannot Self-Correct
Reasoning Yet" (arXiv:2310.01798), "When Can LLMs Actually Correct Their Own
Mistakes" (TACL 2024), Self-Refine (Madaan 2023), Reflexion (Shinn 2023).

| Corrector setup | Finding | fix_rate σ | Source |
|---|---|---|---|
| Self-correction, NO external feedback | at/below baseline; can degrade | 0.10 / 0.30 / 0.55 | arXiv:2310.01798 |
| Correction WITH reviewer feedback | materially improves over baseline | 0.55 / 0.70 / 0.85 | TACL 2024 |
| Agentic re-do with test/oracle signal | high when signal is reliable | 0.65 / 0.78 / 0.90 | Reflexion 2023 |

**Key result (SOURCED, multiple papers agree).** Intrinsic self-correction
without an external signal is unreliable — `fix_rate` collapses toward baseline.
This is exactly why the cockpit splits *detection* (reviewer) from *repair*
(corrector): a corrector with no reviewer feedback has a low `fix_rate`, and
`σ_corr = σ_raw + (1−σ_raw)·catch_rate·fix_rate` makes that visible.

---

## GAP 5 — Modern RAG + agentic component taxonomy

Anchors: Lewis et al. RAG (2020), ReAct (arXiv:2210.03629), Self-Refine,
Reflexion, Berkeley "Compound AI Systems"
(<https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/>), agentic
surveys (arXiv:2404.11584, 2506.04565). The node types the cockpit should model:

| Component | LLM-backed? | Quality metric | Bucket |
|---|---|---|---|
| Generator (draft/code/extract) | yes | pass@1 / faithfulness / F1 | generator |
| Query rewriter / expander | yes | retrieval uplift | generator |
| Embedder | **no** (vector model) | MTEB/BEIR nDCG@10 | retriever |
| Vector retriever | **no** (ANN search) | recall@k / nDCG@10 | retriever |
| Reranker | either | post-rerank nDCG@10 | reranker |
| Router / classifier / intent | yes | accuracy / F1 | router/classifier |
| Reviewer / judge | yes or human | catch_rate (detect) | reviewer/judge |
| Corrector / refiner | yes | fix_rate (repair) | corrector |
| Tool / function caller | yes | call success / BFCL | tool-caller |
| Planner / decomposer | yes | plan validity | planner |
| Memory | **no** (store) | retrieval accuracy | memory |
| Groundedness / citation verifier | yes | faithfulness | verifier |

**The two corrections the cockpit needed:** (1) retrieval is an embedder +
vector search, *not* an LLM — an LLM only enters retrieval as a *reranker*
(post-ranking) or *generator* (reader); (2) reviewer ≠ corrector — detection and
repair are separate competences whose **product** governs corrected quality.
