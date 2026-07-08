# LAYER 0 — DECISION RECORD · Adaptive review cockpit showcase

> Product owner sign-off on the three design layers
> (`01-flowcharts.md`, `02-lowfi-mocks.md`, `03-frontend-plan.md`)
> against the approved spec (`COCKPIT_ONLINE_SHOWCASE.md`).
> Every contested number below was **re-derived live** from the actual modules
> before signing (see "Numbers I personally re-verified").
> Status: **APPROVED TO BUILD** (one waiver, two gates that decide at build time).

---

## 0. Numbers I personally re-verified (the trust contract, checked not asserted)

Run against `scripts/online_skirental.py` (loaded by path) and the `src/minimal_oversight`
package (`tracking.py`, `caching.py`). All figures the committee disputed resolve in
favour of the **final** docs, which already absorbed the fixes:

| Quantity | Re-derived value | Where it must appear | Verdict |
|---|---|---|---|
| Ratchet CR @ **τ=320** (W=1,λ=10,ncyc=20) | **14.92** | hero stamp, anchor tick, index card, step-1 gate | ✅ lands on published **14.9** |
| Ratchet CR @ τ=332 (duty exactly 0.003) | **15.48** | — | ✅ correctly **forbidden** (would corrupt the headline) |
| Full-instance **dwell@2λ** ratio (LIVE teal line) | **1.88** | the flat teal controller line + story card | ✅ distinct from the bound |
| Per-phase bound **2−1/(2λ)** at λ=10 (GHOST tick) | **1.95** | dashed-grey ghost + details row | ✅ "can approach, never cross" |
| Bound at λ=1/5/10/20 | **1.50 / 1.90 / 1.95 / 1.975** | Advanced λ ghost ticks | ✅ exact |
| Tracking floor **z·√P\*** (the WALL + floor card) | **0.1267** | drawn floor line + locked card | ✅ commensurable with the band |
| Tracking **√(νσ)** (theory-only ORDER) | **0.0632** | "see the theory" reveal ONLY | ✅ never the cold-open card/line |
| Tracking deadband **z·σ** / penalty √(σ/ν) | **0.411 / 3.16** | details row | ✅ ratio **3.24×** (the 5s story) |
| Caching LRU anchors (rounds=400) | **{2:1.997 … 8:7.877}** (~h) | reveal anchor ticks | ✅ exact |
| Caching MARKER anchors vs H_h | **{4:2.06 … 32:3.88}** below **{…4.06}** | reveal: live ticks + dashed H_h | ✅ converging, never on H_h |
| `nd()` assigns `drift_rate` from template `drift:` (cockpit L198/652/669) | present | capstone driver | ✅ grep target correct |
| Connector library carries real vendor names (HubSpot/Salesforce/Stripe/Auth0/Plaid) | present | — | ✅ registry-leak risk is **real** → masking guard justified |

**Conclusion of verification:** the committee findings describe the *raw* concepts; the
**final** three layers are the *fixed* versions and are internally consistent with the
module math. No blocker survives in the documents as written. I am signing the fixed package.

---

## 1. SIGN-OFF

**Verdict: the package SHIPS.** Across the five external-adopter criteria:

- **Compelling — YES.** The hero (ski-rental duty sweep: one cause, two forking effects,
  a red line that runs off-frame stamped "unbounded · 14.9× and rising" beside a flat teal
  "pays 1.88×") delivers bounded-vs-unbounded pre-verbally in under three seconds. This is the
  single killer gesture both adversarial critiques named; the package leads with it everywhere.
- **Accessible — YES.** Every chart carries a plain-language headline strip; every headline
  number prints its direction ("1.0 = matches a perfect oracle · higher = worse"); jargon
  (LRU, Belady, clairvoyant, Kalman, deadband, bottleneck, competitive ratio, H_h) is glossed
  inline at first use; axis labels are in words ("safety margin you must hold", "review pool =
  how many you can watch at once"). A zero-theory reader can scan, drag one knob, and "get it".
- **Simple — YES.** Exactly ONE visible slider per widget on load; every other knob is collapsed
  behind a "More controls"/"Advanced" disclosure; ONE big story-number card with intermediates
  demoted to a small details row; the secondary "see the theory" chart is a reveal, never the
  cold-open. This is the anti-flight-deck discipline that lifts the raw 6/10 concepts, enforced
  in code by the build gates.
- **Scientifically precise — YES, and machine-checked.** Every displayed number is recomputed
  live by `adaptive-online.js` (a literal port), pinned to the Python reference by `tests/test_parity.py`
  at |Δ|<1e-6 (caching's asymptotic anchors by a documented convergence band, not 1e-6). The
  LIVE-vs-GHOST discipline (realized cost 1.88 on the curve; proven bound 1.95 as a dashed ghost;
  finite-sample MARKER ticks distinct from the H_h asymptote) is correct and load-bearing for the
  anchor-vs-live trust overlay. The 14.9-vs-0.003 hazard is resolved by pinning τ=320 (verified).
- **Appealing to external adopters — YES.** Neutral titles, decision-framed copy ("which funded
  agent do you cut?"), an attract-loop that hooks before handing over the knob, and a
  reduced-motion path that keeps every widget legible without animation.

**What blocks "ship": nothing at the package level.** Two items are deliberately *deferred to
build-time evidence* rather than blocking now: (a) the **tracking ship-or-paper-figure gate**
(decided by the 5-second test on the real widget — see §2.1); (b) **green parity** (no widget
ships on a red gate — see §3). One scope item (masking A/B) is waived out of v1 by decision.

---

## 2. DECISIONS (go / cut / sequence — each with a one-line rationale)

### 2.1 Tracking: SHIP-OR-PAPER-FIGURE gate — **CONDITIONAL SHIP, re-based, gate at build time**
- **Decision:** Build tracking LAST of the three widgets, re-engineered to the **band-thickness**
  cold-open ("same safety, 3.2× more wasted holding": fat amber z·σ=0.411 vs thin teal z·√P\*=0.127),
  with the drawn noise-floor wall at **0.127** and a "can't go lower" locked card. Then run the gate.
- **The native punchline is CUT** (rationale: "the floor √(νσ) never prints 0.00" is an
  absence-of-collapse non-event — fails the 5-second test).
- **The breach-count framing is CUT** (rationale: mathematically false for the calibrated pair —
  z=Φ⁻¹(0.98) targets ~2% infeasibility for *both* policies by construction; verified deadband
  ≈1.93% vs Kalman ≈2.04–2.09%, so the deadband does **not** breach more; ~2 flashes each is a
  speckle, not a wall). Red breaches are kept only as faint secondary texture with **no**
  "breaches more" claim.
- **THE MEASURABLE BAR THAT DECIDES IT (binding):** On a ≤5-second glance at the built widget's
  cold-open, a zero-theory viewer must read **"the naive way wastes a pile of holding for the same
  safety, and there is a hard floor it can't beat"** — i.e. (i) the amber band is *visibly* ~3×
  the teal band's half-height, AND (ii) the teal band visibly bottoms out ON the drawn floor line
  as ν→0 (the floor reads as a wall, like INFEASIBLE). If **both** read in <5s → **SHIP** as
  `web/widgets/tracking.html` (arc hop ④, index card). If the band gap is too subtle / no felt
  failure without the opt-in under-margin probe → **CUT from the showcase, keep the math as a
  paper figure**; do **not** ship a flat third widget. Parity stays green either way.
- **Rationale:** a remembered wall + a visible fat-vs-thin gap are 5-second events; an unread
  number and a 2% breach speckle are not. Better to ship 2 sharp widgets + capstone than 3 with
  a flat one.

### 2.2 Hero-first build order — **GO, hero is step 3 (first widget), gates everything downstream**
- **Decision:** `adaptive-online.js` (step 1) → parity fixtures (step 2) → **hero `skirental.html`
  (step 3)** → caching (4) → tracking (5) → index/nav (6) → cockpit capstone (7).
- **Rationale:** validate the single killer gesture in <3s before investing in anything that
  depends on the module; the hero is the cold-open the entire arc leads with, and proving it
  early de-risks the capstone.

### 2.3 Cockpit "Online" capstone — **IN v1, but BUILD LAST (deferred within the sequence)**
- **Decision:** Included in v1 as the capstone (arc hop ⑤), built strictly **after** widgets 3–5
  validate the module. Promotes the already-present inert per-node `drift_rate` field (no new
  slider; one new `.seg` Static|Online toggle), reuses `mso-core.analyzePipeline` min-over-sinks,
  needs 1–2 purpose-built multi-sink templates.
- **Rationale:** it is what makes the three standalone demos read as the *time-extension of the
  flagship* rather than a detour — high payoff — but building it first risks turning a killer demo
  into an unreadable dashboard, so it is deliberately last. (If schedule slips, it is the natural
  v1.1 cut line, since the three widgets + index stand alone; that is a fallback, not the plan.)

### 2.4 Masking Agent-A/B governance surface — **DEFERRED (out of scope for v1)**
- **Decision:** Does **not** ship in this showcase. It is not one of the spec's five deliverables;
  it appeared only as an "if surfaced" hedge, which is dropped across all three layers.
- **Rationale:** asserting an anonymization guarantee against a surface that does not ship is
  confusing and unbuildable. The guarantees that DO bind v1 are concrete and retained:
  `adaptive-online.js` must not import `mso-registry.js`/`mso-priors.js`, and no new artifact carries
  vendor names. If A/B is ever added later it MUST be its own one-slider widget computing bare
  "Agent A"/"Agent B" live via `mso-core.maskingIndex`/`sigmaCorrFixedPoint`, importing no
  registry/priors. (The leak risk is real — verified the connector library carries
  HubSpot/Salesforce/Stripe/Auth0/Plaid.)

### 2.5 Hero operating point — **PIN τ=320 (duty ≈0.003), forbid τ=332**
- **Decision:** The hero instance is W=1, λ=10, ncyc=20; the slider's far extreme is **τ=320**
  (duty 1/321 = 0.0031, displayed "≈0.003"), where ratchet CR = **14.92** → lands on the published
  **14.9** tick. The slider must **not** reach τ=332 (CR=15.48 there).
- **Rationale:** the anchor-vs-live overlay requires the live curve to visibly LAND on the 14.9
  tick; 14.9-at-duty-0.003 (τ=332) is internally false (15.48) and would either fail the parity
  gate or silently corrupt the headline. Verified both values; the docs already pin τ=320.

### 2.6 Parity is the release gate — **GO, no widget ships on a red gate**
- **Decision:** `adaptive-online.js` is parity-pinned by three new `tests/test_parity.py` fixtures
  before any widget is accepted. Ski-rental full-instance forms are promoted from
  `scripts/online_skirental.py` (loaded via `importlib.util.spec_from_file_location`, since
  `scripts/` has no `__init__.py` and these forms are absent from the package); tracking/caching
  reference the package modules.
- **Rationale:** "the browser math equals the reference math, machine-checked" is the
  differentiator; it cannot be a red gate at ship.

---

## 3. ACCEPTANCE CRITERIA (definition of done, per deliverable)

A reviewer checks each box. **Design-law checks (L1–L8) and anonymization checks (A1–A3) recur per
widget** and are listed once here, then referenced:

> **Design laws (verify on every widget):**
> **L1** exactly ONE visible slider on load; every other knob behind a `<details>` "More
> controls"/"Advanced". **L2** plain-language `.banner` headline strip above the chart. **L3**
> direction printed on the headline number ("1.0 = matches a perfect oracle · higher = worse", or
> tracking's "can't go lower"). **L4** ONE big `.card .v` story-number; P\*/bound/penalty/z·σ demoted
> to a `.muted` details row; the card shows the **realized** value, never a bound dressed as the cost.
> **L5** jargon glossed inline at first use; axis labels in words; competitive ratios qualified
> "worst-case / against an adversary". **L6** the "see the theory" chart is a reveal, not the
> cold-open. **L7** the failing line runs off-frame stamped "unbounded"/"INFEASIBLE"; **no axis
> auto-rescale to contain it**; floor LINE and floor CARD are the same commensurable quantity.
> **L8** locked color semantics (teal=feasible/held/hit/funded · amber=margin/holding · red=miss/
> infeasible/breach · blue=online estimate · dashed-grey=offline optimum/analytic floor/asymptote).
>
> **Anonymization (verify on every new artifact):** **A1** zero author/venue/repo/arXiv strings in
> the new file. **A2** `adaptive-online.js` does not `require`/import `mso-registry.js` or `mso-priors.js`.
> **A3** benchmark numbers appear only as faint anchor ticks the live module lands on — never
> hard-coded lookups.

### 3.1 `web/adaptive-online.js` (+ parity green)
- [ ] `node -e "require('./web/adaptive-online.js')"` loads clean; exports `window.AdaptiveOnline` via the
      same UMD wrapper as `mso-core.js` (**code wrapper only — NOT** the author/reference header).
- [ ] Ports all ski-rental per-phase helpers + full-instance forms (`requiredSeq`, `optCost`,
      `dwellCost`, `ratchetCost` via the `run("ratchet",…)`+`cost(...)` path), all tracking fns +
      `KalmanTracker`, all caching fns + `SharedPoolController`; MARKER RNG = mulberry32 (not NumPy).
- [ ] `AdaptiveOnline.skirentalRatio(10) === 1.95`; **`ratchetCost(1,320,10,20)/optCost(1,320,10,20)`
      satisfies `|x−14.9| < 0.05`** (do NOT assert ≈14.9 at τ=332); `noiseFloorPerStep(0.02,0.20) ≈ 0.127`.
- [ ] `pytest tests/test_parity.py` green: ski-rental (incl. the hero point `(1,320,10,20)`) and
      tracking scalars + Kalman trajectory at |Δ|<1e-6; LRU/Belady/ratchet/`SharedPoolController('lru')`
      integer-equal; MARKER **deterministic** under fixed seed + a **golden-vector** exact check +
      **seed-averaged convergence** to H_h within a documented band (≈0.25 at rounds=400, **not** 1e-6).
- [ ] **A1, A2** hold (`grep -L 'registry\|priors\|Azevedo' web/adaptive-online.js` returns the file).

### 3.2 `web/widgets/skirental.html` (HERO)
- [ ] **THE GESTURE:** dragging duty toward ≈0.003 (τ→320) **forks the two lines** in <3s — the red
      ratchet escapes the frame stamped **"unbounded · 14.9× and rising"** (L7, no rescale), the teal
      `dwell@2λ` stays flat at its **LIVE 1.88×** hugging the dashed 1.0 clairvoyant.
- [ ] LIVE-vs-GHOST honored: the teal line lands on **1.88** (realized); **1.95** = the proven bound
      drawn as a dashed-grey ghost + details-row label ("can approach, never cross"), never on the card.
- [ ] The live curve lands on the `skirentalRatio` anchor ticks; the λ ticks 1.50/1.90/1.975 are
      reachable **only** via the Advanced λ slider (the one cold-open knob = duty, λ=10 fixed).
- [ ] **L1–L8** all hold; "never more than 2×" kept as the correct worst-case statement.
- [ ] reduced-motion renders the forked end-state with the 14.9 stamp. **A1, A3** hold.

### 3.3 `web/widgets/caching.html`
- [ ] **Two lanes only** by default (LRU vs MARKER) on the same `cyclicAdversary` stream + seed;
      LRU visibly evicts the next-requested slot while MARKER dodges; HIT=teal pulse, MISS=red flash.
- [ ] Belady is a single dashed yardstick **number, not a fourth lane**.
- [ ] **Aha = flash-density only** (LRU reddening vs MARKER staying teal); the quantitative
      dot-convergence overlay is demoted to the reveal, not shown at the climactic beat.
- [ ] **Ratchet wall = its own beat:** held-slot stack crosses the hard red "pool capacity h" line →
      stamps **INFEASIBLE** when distinct sinks > h (L7, no rescale).
- [ ] **Two distinct overlay objects in the reveal:** live empirical dots land on the **finite-sample**
      anchors (LRU {…7.88}, MARKER {2.06,2.68,3.28,3.88} at rounds=400/8 seeds); **H_h**
      {2.08,2.72,3.38,4.06} drawn **separately** as the dashed asymptote the curve only approaches.
- [ ] Competitive ratios glossed **worst-case / against an adversary** at first use. **L1–L8, A1, A3** hold.

### 3.4 `web/widgets/tracking.html`  *(ships only if §2.1 gate passes)*
- [ ] **Cold-open = band thickness:** fat amber deadband band (z·σ=**0.411**) beside thin teal Kalman
      band (z·√P\*=**0.127**) on the same stream; headline "same safety, 3.2× more wasted holding".
- [ ] **The drawn floor wall and the locked floor card are BOTH 0.127** (= `noiseFloorPerStep`, the
      commensurable quantity the teal band bottoms out on); card stamped **"can't go lower"** (L7).
- [ ] **√(νσ)=0.063 appears ONLY** in the "see the theory" reveal as a separate lower dashed "order"
      line — never as the cold-open card or wall.
- [ ] Red breaches are faint secondary texture with **no "breaches more" claim**; **no fixed breach
      integers** as canonical anchors (if shown at all, framed live as "this run", both ≈2%).
- [ ] Every tracking quantity derived from √P\* / `kalmanSteadystateVar` so the ν slider stays correct.
- [ ] **§2.1 5-second bar met** (3× band gap obvious AND floor reads as a wall). **L1–L8, A1, A3** hold.

### 3.5 `web/index.html` attract-loop (+ `mkdocs.yml`)
- [ ] New "Online oversight controllers" section below the existing 7-card grid; sequence-framing copy
      verbatim ("The cockpit showed WHAT to allocate at rest. These three show WHEN to hold, release,
      and evict as things change.").
- [ ] Oversized auto-playing ski-rental hero card: sweeps duty to the fork (τ→320) with zero
      interaction, **freezes at the fork**, stamps "bounded vs unbounded · 14.9×", fades in
      "now you try →"; honors `prefers-reduced-motion` (static frozen fork, same message).
- [ ] **Number consistency (load-bearing):** the card stamps the **same 14.9×** the standalone hero
      renders and the teal line sits at the **same 1.88** — one rendered value per quantity everywhere.
- [ ] caching + tracking teaser cards link to the widgets; mkdocs nav adds the "Adaptive controllers" group.
- [ ] **A1** holds for the NEW section (pre-existing `index.html` strings L11/L23 are intentionally
      retained for the public OSS build, out of scope; scrub only for a blind-paper build).

### 3.6 `web/widgets/cockpit.html` Online mode (capstone)
- [ ] Adds exactly ONE new control — a `.seg` **Static | Online** toggle (Static = default, byte-identical
      to today); **no new slider** (reuses the existing inert per-node `drift_rate`, keyed `drift:` on
      templates, assigned by `nd()` at L198, inspector L652, listener L669).
- [ ] Online mode: the red bottleneck dot **moves** between sinks under drift (reuses `lastBottleneck`
      red dot, L594); per-sink budget bars breathe (teal held / amber required tick); pool occupancy
      animates against the `h` cap; hold(teal)/release(red) events fire.
- [ ] Reuses `mso-core.analyzePipeline` min-over-sinks (**does not re-derive** delivered quality);
      adds 1–2 purpose-built multi-sink templates (so the bottleneck has somewhere to move).
- [ ] Headline strip "Online · the bottleneck is moving under drift"; readouts in the existing
      `theory-readout`/`recipes` panel. reduced-motion renders a static Online snapshot. **A1** holds
      for the new wiring (pre-existing footer L131 intentionally retained, out of scope).

---

## 4. BUILD CHECKLIST (ordered, dependency-correct — maps to front-end plan §f)

1. **`web/adaptive-online.js`** — port all three modules + `KalmanTracker` + `SharedPoolController`; UMD
   code wrapper only (no author header); mulberry32 for MARKER; no registry/priors import. *(Gate 3.1
   load + scalar checks.)* **Blocks everything.**
2. **`scripts/online_parity_runner.js` + `tests/test_parity.py` fixtures (×3)** — separate runner that
   requires only `adaptive-online.js`; load ski-rental full-instance forms from `scripts/online_skirental.py`
   via `importlib` (or add `scripts/__init__.py` — pick one, document it); tracking/caching from the
   package; deterministic-exact + caching convergence band + MARKER golden vector. *(Gate 3.1 pytest
   green.)* **Gates every widget below.**
3. **HERO `web/widgets/skirental.html`** — duty sweep, two `<polyline>` lines, ONE slider (τ/duty,
   extreme τ=320), Advanced in `<details>`, headline strip, one story card, off-frame "unbounded" stamp.
   *(Gate 3.2; ships only when the fork reads in <3s AND step-2 parity green.)*
4. **`web/widgets/caching.html`** — two-lane spotlight race on `cyclicAdversary`; ratchet wall as its
   own beat; Belady a dashed number; CR-vs-h reveal with H_h as a separate dashed asymptote; "lengthen
   stream" probe. *(Gate 3.3; parity green.)*
5. **`web/widgets/tracking.html` (CUT-GATE)** — Kalman vs deadband on one stream; fat-vs-thin bands as
   the cold-open; drawn floor line + locked card at 0.127; corrected breach texture. **Run the §2.1
   5-second test → SHIP or demote to paper figure.** *(Gate 3.4; parity green either way.)*
6. **`web/index.html` + `mkdocs.yml`** — "Online oversight controllers" section, auto-play hero card,
   sequence copy, caching+tracking cards (drop the tracking card iff step 5 cut), nav group. *(Gate 3.5.)*
7. **Capstone `web/widgets/cockpit.html`** — promote `drift_rate` into a Static|Online `.seg` toggle;
   moving bottleneck dot + breathing budget bars + pool occupancy; reuse `analyzePipeline`; add 1–2
   multi-sink templates. **Built last, only after widgets 3–5 validate the module.** *(Gate 3.6.)*

**Global gate on every step:** the recurring L1–L8 and A1–A3 checks in §3 must pass; nothing ships on
a red parity gate.

---

## 5. RESOLUTION — scientific precision vs product simplicity (the rule the team follows)

These two goals collided in three concrete places (the 1.95 bound vs the 1.88 realized cost; the
0.063 order vs the 0.127 floor; the finite-sample MARKER ticks vs the H_h asymptote). The resolution
is **not** to drop precision for punch, nor to crowd the cold-open with every exact quantity. The
governing rule:

> **THE COLD-OPEN CARRIES EXACTLY ONE TRUE, REALIZED, COMMENSURABLE NUMBER PER STORY; EVERY OTHER
> EXACT QUANTITY (BOUNDS, ASYMPTOTES, ORDERS, INTERMEDIATES) IS PRESERVED VERBATIM BUT DEMOTED TO A
> DETAILS ROW OR A "SEE THE THEORY" REVEAL. PRECISION IS NEVER SACRIFICED — IT IS RE-LOCATED.**

Operationally, four sub-rules make this unambiguous:

1. **Realized over bound, on the curve and the card.** The line and the story-number card show the
   value the system *actually pays this run* (ski-rental **1.88**, tracking floor **0.127**). The
   proven *bound*/asymptote (1.95 = 2−1/(2λ); H_h; √(νσ) order) is drawn as a **dashed-grey ghost**
   the live value approaches and labeled as a bound in the details row — never dressed as the cost.
2. **Commensurable units on any "lands on / bottoms out on" claim.** A band drawn in margin units
   (z·√P\*) may only rest on a line in the same units (0.127), never on an RMSE-order quantity (0.063).
   If two numbers are not in the same units, they may not share a visual baseline.
3. **One rendered value per quantity, everywhere.** The same number (14.9×, 1.88×, 0.127) appears
   verbatim in the headline, the stamp, the anchor tick, the card, and the index — because the
   anchor-vs-live overlay is a *trust* feature; a 15× sentence over a 14.9× line silently breaks it.
4. **Worst-case stays labeled; precision implies honesty, not just digits.** Every competitive-ratio
   headline carries "worst-case / against an adversary" at first use; a claim the calibration math
   contradicts (the deadband "breaches more") is cut even though it would be more dramatic — being
   scientifically precise *includes* refusing a false but punchy framing.

This rule is what reconciles "compelling/simple" with "scientifically precise": the adopter scans one
honest realized number and a wall; the exact theory is one disclosure-click away, intact, and
machine-checked at |Δ|<1e-6.

---

**SIGNED OFF — product owner. Build in the order of §4; tracking decided by the §2.1 bar at step 5;
masking A/B waived to a future revision; nothing ships on a red parity gate.**
