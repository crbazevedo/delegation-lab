# How the priors are built

When you have no traces yet, the cockpit still needs *starting numbers* for each
node. This page explains exactly how a public benchmark becomes the number a node
is seeded with — so you can judge it, not just trust it. Every prior is a
**hypothesis to refine with your own traces**, never ground truth. The raw
evidence and citations live in the [Priors Evidence Ledger](priors-evidence.md).

We write the concept first and the symbol in parentheses, e.g. *raw competence
(σ_raw)*. You never need the symbols to use the cockpit; they're there if you
want to follow the math.

---

## The two competences a node has

A node does work, and that work may be reviewed and repaired. We track three
distinct probabilities, because conflating them is the most common governance
mistake:

| Concept (symbol) | Plain meaning | Who owns it |
|---|---|---|
| **Raw competence (σ_raw)** | P(the node is right *on its own*, before any review) | the worker |
| **Reviewer catch rate (c)** | P(a reviewer *detects* an error that exists) | the reviewer |
| **Corrector fix rate (f)** | P(a flagged error is *actually repaired*) | the corrector |

The **corrected quality (σ_corr)** the rest of the workflow sees is:

$$\sigma_{corr} = \sigma_{raw} + (1 - \sigma_{raw}) \cdot c \cdot f$$

In words: start from what the worker gets right on its own, then recover the
errors that are *both* caught *and* fixed. The product **c · f** is the
**effective correction**.

### Why detection and repair are separate

A reviewer that flags every error but hands it to a corrector that can't fix it
(`f` ≈ 0) lifts quality by *nothing*. The published evidence is blunt about this:
intrinsic self-correction *without external feedback* is unreliable and sometimes
makes answers worse, while correction *with* a reliable reviewer signal helps
([evidence](priors-evidence.md#gap-4-reviewers-llm-as-judge-and-correctors-fix-success)).
So the cockpit models a **reviewer** (detection, `c`) and a **corrector**
(repair, `f`) as separate competences. The classic single-number model —
"the reviewer catches *and* perfectly fixes" — is just the special case **f = 1**.

> **Lesson built into the framework:** *corrected* performance is not evidence of
> *autonomous* competence. A node can look healthy (high σ_corr) while its raw
> competence (σ_raw) is poor — the gap is hidden by review. We surface that gap as
> the **masking index (M\* = σ_corr / σ_raw)**.

---

## From a benchmark number to a seed

### Generators → seed the skill (σ_skill)

For a node that *produces* work (drafting, code, extraction, classification,
retrieval, reranking) the prior is a **raw-competence band** σ_raw = (low / mid /
high). But a node in the model is parameterized by its underlying **skill
(σ_skill)**, which the *competence calibration operator* damps toward an equilibrium by the gain
**γ = η / (η + δ) = 10/12 ≈ 0.833** (observation rate η over observation + decay).
At that equilibrium, raw competence is γ · σ_skill. So to make a freshly-seeded
node *reproduce the prior's σ_raw*, we invert the relationship:

$$\sigma_{skill} = \mathrm{clamp}\!\left(\frac{\sigma_{raw}^{mid}}{\gamma},\; 0.05,\; 0.98\right)$$

Then γ · σ_skill = σ_raw at the fixed point, by construction. (The clamp keeps the
seed inside a sane range; when it bites, the round-trip is approximate and the
cockpit says so.)

### Reviewers → seed the catch rate (c); correctors → seed the fix rate (f)

A **reviewer** node is seeded directly with the **catch rate (c)** from its prior
band; a **corrector** node with the **fix rate (f)**. No γ inversion — these are
already probabilities of an event (detect / repair), not competences subject to
the calibration-operator dynamics.

### How wide is the band? → confidence

Each prior is a band, and band width is a crude evidence-strength signal. The
cockpit shows a **confidence = 1 − (high − low)**: a tight band (strong, recent,
absolute evidence) reads as high confidence; a wide band (relative, stale, or
verification-limited evidence) reads as low. Confidence is a *humility meter*, not
a guarantee.

---

## Turning benchmarks into σ: the normalization rules

Not all benchmark numbers mean the same thing. We apply three rules, and record
which one was used in every cell's note.

1. **Absolute metrics → σ directly (with a discount).** pass@1, accuracy, F1,
   nDCG@10, faithfulness rate, and judge↔human agreement are already
   "probability of being right"-shaped. We map them to σ with a modest
   *domain-shift discount*, because leaderboard conditions are friendlier than
   your production data.
2. **Relative metrics → ranking only, never σ.** Arena Elo, win-rates, and
   preference rates order models; they are *not* success probabilities. We never
   invert an Elo into a σ. Relative evidence is used only to *rank* models whose
   scale is already pinned by an absolute benchmark, and any cell resting on it
   carries a wider band.
3. **Bands widen with doubt.** Relative, stale, contaminated, or
   verification-limited evidence → wider band. No public evidence → a deliberately
   wide conservative band flagged **INTERPOLATED**, *never* an invented number.

---

## The component taxonomy

Modern RAG and agentic systems are *compound* — many specialized parts, not one
model. Two corrections matter most for governance:

- **An LLM does not do retrieval.** Retrieval is an **embedder + vector search** —
  not a language model generating text. An LLM's legitimate roles in a retrieval
  pipeline are *reranking* (post-ranking candidates) and *grounded generation*
  (the reader that writes an answer from already-retrieved context).
- **A reviewer is not a corrector.** Detection and repair are different jobs with
  different success rates (see above).

| Node type | Language model? | What it's scored on | Seeds |
|---|---|---|---|
| Generator (draft / code / extract) | yes | pass@1 / faithfulness / F1 | σ_skill |
| Classifier / router | yes | accuracy / F1 | σ_skill |
| **Embedder / retriever** | **no** — vector model + ANN search | MTEB / BEIR nDCG@10 | σ_skill |
| Reranker | cross-encoder *or* listwise LLM | post-rerank nDCG@10 | σ_skill |
| Grounded generation (RAG reader) | yes | faithfulness | σ_skill |
| **Model reviewer (LLM-as-judge)** | yes | catch rate (detection) | c |
| Human reviewer | no (person) | catch rate (detection) | c |
| **Corrector / refiner** | yes | fix rate (repair) | f |

The retrieval, reranking, and grounded-generation distinctions all flow from the
[component-taxonomy evidence](priors-evidence.md#gap-5-modern-rag-agentic-component-taxonomy).

---

## Honest caveats

- **Judge catch rate is the softest column.** LLM-as-judge agreement with humans
  is noisy and biased (position, verbosity, self-preference). Ensembling several
  judge calls helps materially, but treat every catch-rate prior as a wide guess
  until your traces say otherwise.
- **Retrieval σ is corpus-dependent.** MTEB/BEIR numbers are leaderboard
  upper-bounds; your corpus and query distribution will differ. Recency hurts:
  rerankers drop measurably on novel queries.
- **Reasoning ≠ faithful.** Reasoning model variants hallucinate *more* than their
  base siblings on grounded tasks; a "smarter" model can be a *worse* drafting
  prior. The priors encode this.
- **Self-correction without feedback is unreliable.** A corrector with no reviewer
  signal has a low fix rate by design.
- **INTERPOLATED cells are not measurements.** Where a model has no public
  benchmark (e.g. an unreleased name), its band is interpolated from the nearest
  benchmarked sibling and flagged. Refine it from your own traces first.

**The one-line method:** map a *cited* benchmark to a σ band under explicit
normalization rules, invert through the calibration-operator gain to seed the node,
keep detection and repair separate, and widen the band whenever the evidence is
weak — then let your traces overwrite all of it.
