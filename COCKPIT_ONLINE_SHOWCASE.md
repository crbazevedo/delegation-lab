# Adaptive review cockpit — killer-features showcase (design spec)

> **Status:** proposal for review. Nothing here is committed or built yet. The online modules
> (`skirental`, `tracking`, `caching`, `online_control`) already ship as tested Python on
> `feat/adaptive-review-variants`; this spec is the plan to make them *visible and probe-able* in the
> web cockpit. Generic — no paper prose. Benchmark numbers below are the anonymized values already
> present in the code/tests.

## TL;DR — one decision, then build in order

The cockpit and its seven widgets are **static/equilibrium** — they have no notion of time, drift,
an adaptive controller, or a finite review pool. The entire online result is invisible in the
interactive layer. The plan adds **one new UMD math module + three standalone widgets + an index
attract-loop**, then folds it all into the cockpit as a capstone.

Two adversarial critiques (a product/wow lead and a cold first-time visitor) independently landed on
the **same verdict**: the per-module concepts are individually compelling but, as drawn, are a
*flight-deck* — 4–6 sliders, multiple charts, insets, and 4 metric cards per screen, against
shipping widgets that have **one chart and one knob**. Both scored 6/10 raw. The fix is the same
from both: **ship one killer gesture, protect it from clutter, gloss the jargon, put direction on
the number.** This spec is the post-fix plan.

## The hero

**The Ski-Rental Duty Sweep — "watch it break."** One chart, two lines, **one** slider.

Drag the slack-duty knob toward `0.003` and the never-release **ratchet** cost line climbs a
diverging ramp and runs *off the top of the frame* (no axis rescale) stamped **"pays 14.9× and
rising · unbounded"**, while the **2λ controller** line stays a flat teal band just above a dashed
clairvoyant-optimum, with one big card reading **"pays 1.95× the best-possible."** Both critiques
named this *the* single killer moment: one cause, two visibly forking effects, the whole
"bounded vs unbounded" thesis delivered pre-verbally in **under three seconds**, with the proven
bound as a ghost tick the viewer keeps bumping into but can never beat.

## The five features

| # | Feature | Wow | Effort | Role |
|---|---------|:---:|:------:|------|
| 1 | **Ski-Rental Duty Sweep** | 9 | M | Cold-open hero |
| 2 | **Cache Eviction Race + Ratchet Wall** | 8 | L | Most legible mechanism |
| 3 | **Index Attract-Loop** (30s auto-play) | 7 | S | Hook before the knob |
| 4 | **Cockpit Online Mode** | 7 | L | Capstone — build last |
| 5 | **Tracking: the Noise Wall** | 6 | M | Conditional ship (see below) |

### 1 · Ski-Rental Duty Sweep (hero)

- **Decision named:** *"A reviewed agent recovered. Keep paying to hold its review budget, or
  release it and risk re-paying if it relapses?"*
- **The one knob:** slack duty cycle, with a `Drag this →` callout. λ, dwell-override, and K-sinks
  collapse behind a **"Advanced: why exactly 2λ?"** disclosure.
- **Effect made vivid:** the ratchet's held review diverges without bound as slack shortens; the 2λ
  controller stays inside the proven `2 − 1/(2λ)` factor. One line forks to the ceiling, the other
  goes flat on the optimum. **Don't rescale the axis** — let the failing line escape the frame and
  stamp "unbounded." A trace that runs off-plot is remembered; "14.9" is not.
- **Data (pure scalars, zero identity):** `dwell* = 2λ`; `ratio = 2 − 1/(2λ)` → 1.50 / 1.90 / 1.95 /
  1.975 at λ = 1 / 5 / 10 / 20; ratchet unbounded → **14.9 at duty 0.003**. Published values appear
  only as faint anchor ticks the *live* curve lands on.
- **Build:** port `skirental.py` verbatim into `web/adaptive-online.js`; widget `web/widgets/skirental.html`
  reuses the `return-operator.html` polyline idiom + the cockpit `requestAnimationFrame` clock.

### 2 · Cache Eviction Race + Ratchet Wall

- **Decision named:** *"Review capacity is finite and the bottleneck keeps moving — which funded
  agent do you cut?"*
- **The one knob:** pool size `h`. A single travelling spotlight walks the moving bottleneck across
  `k` sink chips above `h` funded slots. **Two lanes only** by default — LRU vs MARKER on the *same*
  cyclic-adversary stream and seed — each request a HIT (teal pulse) or MISS (red flash + eviction
  animation). LRU visibly evicts the very slot requested next; MARKER dodges. Belady is a single
  dashed yardstick number, **not** a fourth lane. The **ratchet wall** is its *own* beat: a held-slot
  stack grows past a hard red "pool capacity h" line and stamps **INFEASIBLE** when distinct sinks
  exceed h.
- **Data:** LRU CR `{2:1.99, 3:2.97, 4:3.95, 6:5.86, 8:7.76}` (~h); MARKER `{4:2.06, 8:2.68, 16:3.28,
  32:3.88}` (~H_h). Live empirical miss-ratio dots converge onto these anchors.
- **Critique fix baked in:** four lockstep lanes → two; CR-vs-h analytic chart demoted to a "see the
  theory" reveal; jargon glossed inline (*"review pool = how many things you can watch at once,"
  "LRU = drop whatever you watched longest ago," "clairvoyant = a cheater who already knows the
  future"*).

### 3 · Index Attract-Loop (30s cold-open)

The "Online oversight controllers" index section leads with an **oversized auto-playing hero card**:
it sweeps the ski-rental duty down to the fork with zero interaction, freezes at the moment the
ratchet escapes the frame, stamps "bounded vs unbounded," then fades in `now you try →`. Hook before
you hand over the knob (Ciechanowski/Distill discipline). Respects `prefers-reduced-motion`. Section
copy frames the sequence in plain words: *"The cockpit showed WHAT to allocate at rest. These three
show WHEN to hold, release, and evict as things change."* Effort **S** — pure presentation over
`adaptive-online.js`, no new math.

### 4 · Cockpit Online Mode (capstone — build last)

Promote the cockpit's **inert `drift_rate` field** into the driver of a new `Static | Online`
toggle. In Online mode the red bottleneck dot walks the real `state.nodes` sinks under drift,
per-sink review-budget bars breathe (amber held vs required tick), hold/release events fire on the
graph, and shared-pool occupancy animates against the `h` cap — theory readouts in the existing
`theory-readout/recipes` panel. Reuses `delivered_quality = min over sinks` already computed by
`mso-core.analyzePipeline` (don't re-derive). Needs **1–2 purpose-built multi-sink templates** (most
current templates are single-sink chains, so the bottleneck has nowhere to move). This is what makes
the three standalone demos read as the **time-extension of the flagship**, not a detour.

### 5 · Tracking: the Noise Wall (conditional ship)

- **Decision named:** *"You can't see the true required budget, only a noisy drifting signal — how
  big a safety margin must you hold?"*
- **The native punchline fails the 5-second test.** "The irreducible floor `√(νσ)` ticks down but
  refuses to print 0.00" is a *non-event* — absence-of-collapse reads as nothing, or worse, as
  "about to reach zero." **Both critiques flagged this.**
- **Re-engineered to an honest, still-visible failure — band *thickness*, not breach count.**
  ⚠️ The committee's Chief Scientist cut an earlier "flash RED, the deadband breaches more" framing
  as **mathematically false**: at the calibrated margin (z = Φ⁻¹(0.98)) *both* policies target the
  same ~2% infeasibility (simulated: deadband ~1.93%, Kalman ~2.04%). The true, visible story is
  **"same safety, 3.2× more wasted holding"** — run Kalman vs a naive deadband on the *same* stream
  and show the fat amber deadband band (z·σ ≈ 0.411) against the thin teal Kalman band (z·√P\* ≈ 0.127),
  a 3.2× = √(σ/ν) thickness gap at **equal** feasibility. Draw the **noise-floor wall** the teal band
  bottoms out *on* — label it **z·√P\* ≈ 0.127** (the commensurable quantity; √(νσ) ≈ 0.063 is a
  theory-only dashed "irreducible order" line). Red breaches stay as faint secondary texture, never
  the headline.
- **Decision rule (measured at build):** ship only if the 3× fat-vs-thin band gap is obvious *and*
  the floor reads as a wall in <5s. Else **cut it to a paper figure** rather than ship a flat third
  widget.

## What the critiques changed (the anti-flight-deck discipline)

The raw per-module concepts scored 6/10 purely on overload. The merge enforces, in code, the
existing widgets' one-knob discipline:

1. **Exactly ONE visible slider on load** per widget; every secondary knob collapses behind a
   **"More controls"** disclosure. *This is the feature, not optional polish.*
2. **A plain-language headline strip above every chart** stating the outcome in words — *"pays 15×
   more than necessary and climbing"* / *"never pays more than 2×."* The competitive-ratio number is
   the receipt; the sentence is the claim.
3. **Direction printed on the headline number:** `1.0 = matches a perfect oracle · higher = worse`.
   Without it, green-1.95 and red-14.9 are two meaningless numbers.
4. **One big story-number card**; demote `P*`, `z·√P*`, penalty-factor to a small "details" row.
5. **Jargon glossed inline at first use**; axis labels in words where possible ("safety margin you
   must hold" not `z·σ`).
6. **The secondary "see the theory" chart** (CR-vs-h, the U-curve, floor-scaling) is a *reveal*, not
   part of the cold-open.

## How "it works" is proven (the trust contract)

Every displayed number is recomputed in-browser by `adaptive-online.js`, a **literal port** of the Python
modules — nothing is a hard-coded lookup. Trust is closed two ways: (a) the **anchor-vs-live
overlay** — the live curve visibly lands on the faint published benchmark tick as you drag/lengthen
the stream; and (b) the project's **parity contract** — the identical `adaptive-online.js` runs under Node
in `tests/test_parity.py` asserting `|Δ| < 1e-6` against `scripts/online_skirental.py` /
`online_tracking.py` / `online_caching.py`. "The browser math equals the paper's math" is
machine-checked, not asserted. (Caching CR anchors are *asymptotic*, so the fixture compares
finite-sample convergence, and the UI exposes a "lengthen stream" probe.)

## Build order

1. **`web/adaptive-online.js`** (UMD, `window.AdaptiveOnline`) — port `skirental.py` + `caching.py` +
   `tracking.py` verbatim, same wrapper as `mso-core.js` so it runs under Node. Load-bearing; nothing
   ships without it.
2. **Extend `tests/test_parity.py`** with three fixtures at `|Δ| < 1e-6`. **Gate everything on green
   parity** — the machine-checked browser==paper guarantee is the differentiator.
3. **Hero first:** `web/widgets/skirental.html` (duty sweep, two lines, one slider, overflow stamps
   "unbounded," advanced knobs collapsed). Validate the single killer gesture before anything else.
4. **`web/widgets/caching.html`** — two-lane LRU-vs-MARKER spotlight race + ratchet wall on its own
   beat; Belady a dashed number; CR-vs-h as a secondary reveal.
5. **`web/widgets/tracking.html`** — re-engineered around the visible RED-BREACH failure + drawn
   floor wall. Ship only if the failure reads in <5s.
6. **`index.html`** "Online oversight controllers" section: oversized auto-playing ski-rental hero +
   caching + tracking, sequence-framing copy. Add `mkdocs.yml` nav + the methodology page.
7. **Capstone last:** cockpit `Static | Online` mode — promote `drift_rate`, animate per-sink budget
   bars + moving bottleneck + pool occupancy, add 1–2 multi-sink templates. Only after the three
   standalone widgets validate the module.

## Anonymization guardrails

- **Masking A/B surface must NOT bind to `mso-registry.js` or `mso-priors.js`.** The registry
  contains real vendor model names; keeping "Agent A" / "Agent B" as bare numeric
  competence/repair/delivered values, recomputed live from `mso-core`, is the specific mechanism that
  prevents a leak. `adaptive-online.js` must not import the registry.
- **The four new datasets carry only mathematical fields** (λ, ν, σ, h, CR, dwell, margins, M*, r*).
  New widgets ship with neutral titles ("Online oversight controllers") and **zero** author/venue/repo
  strings; benchmark numbers appear only as faint anchor ticks the live module lands on.
- **Heads-up (pre-existing, outside the new modules):** the agents noted the current `index.html`
  and cockpit footer carry author/repo strings (`Azevedo, 2026`, the GitHub URL, the package name).
  Those are legitimate in your *public* repo — but **any build embedded in or screenshotted for a
  double-blind paper submission needs a scrubbed variant.** Flagging so the showcase build can be
  made blind-clean on demand.

## Risks (and how the plan defuses them)

- **Over-instrumentation** (the dominant risk, flagged by both critiques): if the "one visible slider
  + collapse the rest" discipline isn't enforced *in code*, the hero gesture is buried and the score
  stays at 6. The "More controls" disclosure is the feature.
- **Tracking may not survive the 5-second test** even re-engineered → explicit cut-or-keep gate
  (ship only if the 3× band-thickness gap + the floor wall read in <5s; else paper figure).
- **Jargon** → inline glosses + direction-on-the-number are mandatory, not polish.
- **Caching scope creep** → two lanes by default; analytic chart and ratchet wall are separate reveals.
- **"Moving bottleneck" asserted, not motivated** → one-line gloss + drift shown as the visible cause.
- **Multi-sink template gap** → the capstone needs 1–2 purpose-built multi-sink templates.
- **Parity drift** → fixtures written against the exact `scripts/online_*.py` outputs; finite-sample
  comparison for the asymptotic caching anchors.
- **Capstone-first temptation** → the cockpit Online mode is deliberately last; reordering it forward
  risks turning a killer demo into an unreadable dashboard.
