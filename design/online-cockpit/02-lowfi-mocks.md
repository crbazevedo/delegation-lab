# LAYER 2 — Low-fi wireframes · Adaptive review cockpit showcase

> Monospace box sketches for five surfaces. Every screen obeys the 8 design laws.
> Color legend tokens (locked everywhere): `teal=feasible/held/hit/funded` ·
> `amber=margin/holding-overhead` · `red=refund/miss/infeasible/breach` ·
> `blue=online estimate` · `dashed-grey=offline optimum / analytic floor`.
> Every displayed number is recomputed live by `adaptive-online.js`; published values
> appear ONLY as faint anchor ticks (`· · ·`) the live curve lands on.
> theme.css classes are named per surface. Notation in sketches: `[====]`=`.bar`,
> `(o——o)`=`input[type=range]` (the one `.sl`), `▣`=collapsed `<details>`.

---------------------------------------------------------------------------------
VERIFIED NUMBERS (every figure below is the EXACT module quantity; re-derived live)
---------------------------------------------------------------------------------
TWO KINDS OF NUMBER, never conflated:
  • LIVE value  — what the rendered curve actually lands on (full-instance, this run).
  • GHOST tick  — a proven worst-case BOUND or asymptote the live curve approaches
                  but does not equal; drawn dashed-grey, labelled as a bound.

  SKI-RENTAL (W=1, ncyc=20, λ=10 at the hero operating point)
    LIVE flat controller line   ... full-instance dwell@2λ CR  = 1.882
                                    ( = dwell_cost / opt_cost from online_skirental.py;
                                      stable across τ ≥ 2λ )
    GHOST tick (worst-case bound). proven per-slack-phase CR 2 − 1/(2λ) = 1.95
                                    (λ=1/5/10/20 → 1.50 / 1.90 / 1.95 / 1.975)
                                    "can approach, never cross" — dashed-grey.
    LIVE ratchet at the break ... CR 14.9 at τ=320 (duty ≈ 0.0031 ≈ 0.003), and STILL
                                    climbing as duty → 0 (the published anchor it lands on).
    dwell* = 2λ ; break-even: cumulative rent = re-acquire 2λ.

  CACHING (cyclic adversary, h+1 sinks, rounds=400, mean over 8 seeds)
    LIVE LRU anchors  ........... {2:1.997, 3:2.985, 4:3.976, 6:5.932, 8:7.877}  (≈ h, linear)
    LIVE MARKER anchors ......... {4:2.064, 8:2.684, 16:3.283, 32:3.878}  (finite-sample)
    GHOST H_h asymptote ......... {4:2.083, 8:2.718, 16:3.381, 32:4.059}  (the curve only
                                    reaches these as rounds → ∞ — dashed asymptote)
    Belady (offline optimum) .... 1.0× yardstick (a single dashed number, never a lane)
    ratchet: INFEASIBLE once distinct contending sinks > h.

  TRACKING (ν=0.02, σ=0.20, z=Φ⁻¹(0.98)=2.054)
    P*  = kalman_steadystate_var = 0.003805
    LIVE Kalman margin / FLOOR LINE = noise_floor_per_step = z·√P* = 0.127
                                    ← the drawn wall AND the locked floor card BOTH show this.
    LIVE deadband margin ........ z·σ = 0.411   (= 3.24× the Kalman margin, SAME 98% safety)
    GHOST irreducible order ..... √(νσ) = 0.063  (RMSE-order; the Ω(·) SCALING of the floor —
                                    theory-reveal dashed line ONLY, never the cold-open card/line)
    penalty √(σ/ν) = 3.16 (deadband over-holds by this factor).
    Both policies calibrated to z → each breaches ≈ 2% BY CONSTRUCTION (deadband 1.93%,
    Kalman 2.04%): breach COUNT is not the story; band THICKNESS is.

  MASKING A/B ... OUT OF SCOPE for this showcase (no widget/flow ships — see §footer).

```markdown
================================================================================
(1) skirental.html — THE HERO · "watch it break"
================================================================================

------------------------------- COLD-OPEN STATE --------------------------------
The page loads HERE. One slider. Two flat-ish lines. One story card. No motion
until the user drags (the index attract-loop already played the auto sweep).

┌──────────────────────────────────────────────────────────────────────────────┐
│  When to release a recovered agent's review budget          <h1>             │
│  A reviewed agent recovered. Keep paying to hold its review budget, or release │ <p class="lede">
│  it and risk re-paying if it relapses? Drag the slack knob and watch.          │
│                                                                                │
│  ┌── headline strip ───────────────────────────────────── .banner (teal bg) ─┐│  ← LAW 2 + 3
│  │  The 2λ controller never pays more than 2× the best-possible — guaranteed, ││  HEADLINE WORDS (verbatim):
│  │  even against a worst-case relapse pattern.                                ││  "The 2λ controller never pays
│  │  1.0 = matches a perfect oracle  ·  higher = worse                         ││   more than 2× the best-possible —
│  └───────────────────────────────────────────────────────────────────────────┘│   guaranteed, even against a
│                                                                                │   worst-case relapse pattern."
│   review held (× best-possible)                                                │  direction ON the number:
│  5┤                                                            <svg polyline>  │  "1.0 = matches a perfect oracle
│   │                                                                            │   · higher = worse"
│  4┤                                                                            │
│   │                                  ╭──── "Drag this →" callout ─────╮        │
│  3┤                                  │  shorten the slack to break it │        │
│   │                                  ╰────────────────────────────────╯        │
│  2┤·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· 1.95 bound (ghost)│  ← GHOST tick: worst-case
│   │                                                          ↑ can approach,    │     bound 2−1/(2λ), DASHED-GREY
│   │━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.88 2λ ctlr (LIVE)    │  TEAL solid LIVE line lands on
│  1┤- - - - - - - - - - - - - - - - - - - - - - - - - - - - 1.0 clairvoyant     │  its full-instance value 1.88
│   └──┬─────────┬─────────┬─────────┬─────────┬──────────────────────────────  │  DASHED-GREY = offline optimum
│    long slack ←                          → short slack (more relapses)         │  ← axis label IN WORDS (LAW 5)
│                                                                                │
│  (o═══════════════════════════════════════════════════════o)   slack duty     │  ← THE ONE VISIBLE SLIDER (.sl)
│   ↑ ONE slider · slack duty cycle = how often the agent relapses   0.42        │     LAW 1
│                                                                                │
│  ┌─ STORY CARD ─ .card ──────────┐   ┌─ details row ─ .muted (small) ────────┐ │  ← LAW 4: one big card,
│  │ pays 1.88×        .card .v    │   │ worst-case bound 2−1/(2λ) = 1.95×     │ │     intermediates demoted
│  │ 1.0 = perfect oracle,         │   │ (the ghost line it never crosses)    │ │  STORY-CARD reads the LIVE
│  │ higher = worse    .card .l    │   │ dwell* = 2λ = 20 · break-even rent=2λ │ │  ratio, NOT the bound:
│  └───────────────────────────────┘   └───────────────────────────────────────┘ │  v: "pays 1.88×"  (live CR)
│                                                                                │  l: "1.0 = perfect oracle,
│  ▣ Advanced: why exactly 2λ?  ────────────────────────────── <details> closed │      higher = worse"
│                                                                                │  (1.95 = bound → details row,
│  on-widget legend:  ━ 2λ controller (teal, LIVE held right)   - - clairvoyant   │   labelled as the bound, NOT
│      ·· worst-case bound 1.95 (ghost)   ━ ratchet (red, appears on drag →)      │   as the realized cost)
│                                                                                │  ← color legend ON widget (LAW 8)
│  Computed live by adaptive-online.js (skirental.py port), |Δ|<1e-6 vs parity test.  │  ← .foot · FILE NAMES ONLY
└──────────────────────────────────────────────────────────────────────────────┘

   ONE visible slider .................. slack duty cycle (.sl, accent blue)
   "More controls" (▣ Advanced) holds .. λ (1/5/10/20) · dwell override ·
                                         K independent sinks · b rent unit
   color legend ........................ teal=2λ ctlr (LIVE) · dashed-grey=clairvoyant
                                         · red=ratchet · ·· =worst-case bound (ghost)
   LIVE vs GHOST (load-bearing) ........ teal line = full-instance CR 1.88 (what it
                                         actually pays); 1.95 = proven bound 2−1/(2λ),
                                         drawn as a dashed ghost the line approaches.

----------------------------- POST-PROBE STATE ---------------------------------
User dragged duty → 0.003 (τ≈320). The ratchet line is born and RUNS OFF THE TOP.
Axis does NOT rescale (LAW 7). Headline strip flips teal→red. Story card unchanged
(the controller is still fine — that's the whole point).

┌──────────────────────────────────────────────────────────────────────────────┐
│  ┌── headline strip ────────────────────────────────── .banner (RED bg) ─────┐│  ← LAW 2, flipped to failure
│  │  The never-release ratchet pays 14.9× more and is still climbing.          ││  HEADLINE WORDS (verbatim):
│  │  1.0 = matches a perfect oracle  ·  higher = worse                         ││  "The never-release ratchet pays
│  └───────────────────────────────────────────────────────────────────────────┘│   14.9× more and is still climbing."
│                              ▲ ratchet escapes here ▲                          │  (ONE rendered number, 14.9×,
│   review held (× best-possible)        ┊ ┌─────────────────────────────────┐  │   used verbatim in headline +
│  5┤  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╋━│ unbounded · pays 14.9× and rising│  │   stamp + anchor tick + index)
│   │  ╱ (red ratchet, off-frame) ━━━━━━━┛ └─────────────────────────────────┘  │  ← STAMP at the break point
│  4┤ ╱                                                              <polyline>  │     (LAW 7) text verbatim:
│   │╱                                                                          │  "unbounded · pays 14.9× and rising"
│  3┤                                                                  ·· ·· ·· ·│  RED line clipped at frame top,
│   │                                                                           │  NOT rescaled. Published 14.9 anchor
│  2┤·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· ·· 1.95 bound(ghost)│  tick sits ABOVE the frame, faint
│   │━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.88 2λ ctlr (LIVE)    │  at the edge.
│  1┤- - - - - - - - - - - - - - - - - - - - - - - - - - - - 1.0 clairvoyant     │  TEAL still flat at 1.88 — the
│   └──┬─────────┬─────────┬─────────┬─────────┬─────────────────────────────   │  contrast. DASHED-GREY optimum.
│    long slack ←                                  → short slack                 │
│                                                                                │
│  (o═o)══════════════════════════════════════════════════════   slack duty     │  ← slider dragged near 0 end
│   ↑ slack duty cycle = how often the agent relapses              0.003         │     ONE slider, still the only one
│                                                                                │
│  ┌─ STORY CARD ─ .card ──────────┐   ┌─ details row ─ .muted ────────────────┐ │  STORY CARD: UNCHANGED.
│  │ pays 1.88×        .card .v    │   │ ratchet now holds ∞ · never sheds     │ │  The controller card stays teal
│  │ 1.0 = perfect oracle,         │   │ worst-case bound 2−1/(2λ) = 1.95×     │ │  at its LIVE "pays 1.88×" —
│  │ higher = worse    .card .l    │   │ ratchet: no finite bound exists       │ │  bounded-vs-unbounded read
│  └───────────────────────────────┘   └───────────────────────────────────────┘ │  pre-verbally.
│                                                                                │
│  ▣ Advanced: why exactly 2λ?  ─────────────────────────────── still collapsed │
│  Computed live by adaptive-online.js (skirental.py port), |Δ|<1e-6 vs parity test.  │  ← .foot
└──────────────────────────────────────────────────────────────────────────────┘

------------------- "Advanced: why exactly 2λ?" — EXPANDED ---------------------
Reveal only (LAW 6). The secondary "see the theory" U-curve lives in here, never
in the cold-open.

┌──────────────────────────────────────────────────────────────────────────────┐
│  ▼ Advanced: why exactly 2λ?  ────────────────────────────── <details> open   │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │  WORST-CASE factor vs dwell choice d   (the U-curve, against an adversary) │ │  ← SECONDARY chart, REVEAL only.
│  │ 4┤ ╲                                              ╱  rent too long → 2×    │ │  This curve IS the worst-case
│  │  │  ╲                                          ╱                          │ │  CR 2−1/(2λ); its minimum is
│  │ 3┤   ╲                                      ╱                             │ │  the 1.95 ghost line above.
│  │  │     ╲                                ╱                                 │ │  U-shaped: release too early
│  │ 2┤       ╲___                      ___╱                                   │ │  (left, churn) vs hold too long
│  │  │           ╲────●────────────────╱   ● = minimum at d = 2λ (teal dot)   │ │  (right, → ratchet). Minimum
│  │ 1┤- - - - - - - - - - - - - - - - - - - clairvoyant floor (dashed-grey)   │ │  sits exactly at d = 2λ.
│  │   └───┬────────┬────────┬────────┬────────┬──────────────────────────    │ │  TEAL dot = the optimal dwell
│  │   release early ←      d = 2λ      → hold forever (ratchet)               │ │  DASHED-GREY = analytic floor
│  │  (o══════════════════════════o)   λ  (release/re-acquire cost)    10      │ │  ← 2nd-tier slider lives INSIDE
│  │   ·· worst-case bounds: 1.50 / 1.90 / 1.95 / 1.975  at λ = 1 / 5 / 10 / 20 │ │     ghost ticks = the BOUND values
│  │                                                                          │ │     (the live full-instance line of
│  │  Plain words: this is the WORST case — an adversary picks the relapse     │ │     the cold-open lands a touch
│  │  timing to defeat you. Hold too short and you re-pay the 2λ acquire cost  │ │     below each, ≈1.88 at λ=10).
│  │  on every blip (churn); hold forever and you pay rent without bound.      │ │  ← jargon GLOSS inline (LAW 5)
│  │  Renting until cumulative rent equals the acquire cost — at 2λ steps — is │ │
│  │  the safe break-even no adversary can beat.                               │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

   GLOSSES (inline, first use): "slack duty cycle = how often the agent relapses"
   · "clairvoyant = a policy that already knows the future and pays the least"
   · "ratchet = a controller that only ever adds budget, never releases"
   · "2λ = release + re-acquire cost; dwell that long and rent breaks even"
   · "worst-case / against an adversary = the relapse timing is engineered to be
   as bad as possible; on benign timing the controller is far better than 2×"


================================================================================
(2) caching.html — Cache Eviction Race + Ratchet Wall
================================================================================

------------------------------ DEFAULT (BEAT 1) --------------------------------
Two lanes only. One travelling spotlight (▼) walks the moving bottleneck across
the request strip. Each request = HIT (teal pulse) or MISS (red flash). One h
slider. Belady is a single dashed number, not a lane.

┌──────────────────────────────────────────────────────────────────────────────┐
│  Which funded agent do you cut when review capacity runs out?      <h1>       │
│  Review capacity is finite and the bottleneck keeps moving — which funded      │ <p class="lede">
│  agent do you cut? Two policies race on the SAME stream and seed, against a     │
│  stream engineered to be as hard as possible (the worst case).                 │
│                                                                                │
│  ┌── headline strip ───────────────────────────────── .banner (teal bg) ─────┐│  ← LAW 2 + 3
│  │  On a worst-case stream, drop-longest-ago misses ~h× as often as a cheater ││  HEADLINE WORDS (verbatim):
│  │  who knows the future; the dice-roll policy misses only ~ln(h)× more.      ││  "On a worst-case stream, drop-
│  │  1.0 = matches a perfect oracle  ·  higher = worse                         ││   longest-ago misses ~h× as often
│  └───────────────────────────────────────────────────────────────────────────┘│   as a cheater who knows the
│                                                                                │   future; the dice-roll policy
│   moving bottleneck →    ▼ (spotlight walks the stream)                        │   misses only ~ln(h)× more."
│   request stream:  s1  s2  s3  s4  s5  s1  s2  s3  s4  s5  s1 …  (h+1 cycle)   │  ← cyclic adversary, k=h+1 sinks
│                                                                                │     (an engineered worst case)
│  ┌ LRU lane — "drop whatever you watched longest ago" ──────────── pool h=5 ─┐ │  ← inline GLOSS on the lane name
│  │ funded slots: [ s2 ][ s3 ][ s4 ][ s5 ][ s1 ]   ← next request is s2: MISS │ │  LRU evicts the slot needed NEXT
│  │                  ✗ evicts s2 just before it's asked  ●red flash + slide   │ │  RED flash = miss + eviction anim
│  │ HIT ●teal   MISS ✗red    misses so far: 41                                 │ │  TEAL pulse = hit
│  └───────────────────────────────────────────────────────────────────────────┘ │
│  ┌ MARKER lane — "keep a coin-flip memory of what you've seen" ─── pool h=5 ─┐ │  ← inline GLOSS
│  │ funded slots: [ s1*][ s3 ][ s4*][ s5 ][ s2*]   ← s2 still funded: HIT      │ │  MARKER dodges the eviction
│  │                  ●teal pulse · marked slots carry * (recently seen)        │ │  * = marked (protected) slot
│  │ HIT ●teal   MISS ✗red    misses so far: 27                                 │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                │
│  (o═══════════════════════════════════════o)   review pool h                  │  ← THE ONE VISIBLE SLIDER (.sl)
│   ↑ ONE slider · review pool = how many things you can watch at once   5       │     LAW 1 + GLOSS (LAW 5)
│                                                                                │
│  ┌─ STORY CARD ─ .card ──────────┐   ┌─ details row ─ .muted (small) ────────┐ │  ← LAW 4
│  │ misses 4.0×       .card .v    │   │ MARKER 2.1× · Belady (cheater) = 1.0× │ │  STORY-CARD LABEL (verbatim):
│  │ vs a future-knowing oracle,   │   │ - - - Belady yardstick: 38 misses    │ │  v: "misses 4.0×"
│  │ higher = worse    .card .l    │   │ live LRU/MARKER dots converge → ··    │ │  l: "vs a future-knowing oracle,
│  └───────────────────────────────┘   └───────────────────────────────────────┘ │      higher = worse"
│                                                                                │  Belady = single DASHED number,
│  ▣ Beat 2: the ratchet wall      ─────────────────────────── <details> closed │  not a lane (in details row)
│  ▣ See the theory: misses vs pool size h  ────────────────── <details> closed │  ← TWO reveals collapsed (LAW 6)
│                                                                                │
│  on-widget legend: ● hit (teal)  ✗ miss (red)  * marked slot  - - Belady       │  ← color legend ON widget (LAW 8)
│  Computed live by adaptive-online.js (caching.py port), |Δ|<1e-6 vs parity test.    │  ← .foot · FILE NAMES ONLY
└──────────────────────────────────────────────────────────────────────────────┘

   ONE visible slider .................. review pool h (.sl)
   "More controls" reveals (separate beats, NOT cold-open):
     ▣ Beat 2: the ratchet wall ....... INFEASIBLE wall (own beat, sketch below)
     ▣ See the theory: CR-vs-h ........ analytic chart (sketch below)
   inside "More controls" (knobs): stream length (lengthen-stream probe) ·
                                   MARKER seed · rounds · k distinct sinks
   color legend ........................ teal=hit/funded · red=miss/evict ·
                                         dashed-grey=Belady · ·· =published CR

----------------------- ▣ Beat 2: the ratchet wall — EXPANDED -------------------
Its OWN beat (LAW 6 / spec). Held-slot stack grows past a hard red capacity line
and STAMPS INFEASIBLE when distinct sinks exceed h. Axis does not rescale (LAW 7).

┌──────────────────────────────────────────────────────────────────────────────┐
│  ▼ Beat 2: the ratchet wall  ─────────────────────────────── <details> open   │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │  ┌─ headline ─ .banner (RED) ─────────────────────────────────────────┐  │ │  HEADLINE WORDS (verbatim):
│  │  │  Never releasing means holding every sink at once — past h, the     │  │ │  "Never releasing means holding
│  │  │  pool can't fit it. INFEASIBLE.                                      │  │ │   every sink at once — past h, the
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │   pool can't fit it. INFEASIBLE."
│  │   held slots (ratchet never sheds)                                        │ │
│  │  ████ s6  ← 6th distinct sink ┌───────────────────┐                       │ │  ← stack grows ABOVE the red
│  │ ═════════════════════════════│  INFEASIBLE        │═══ pool capacity h=5 ═ │ │     "pool capacity h" line,
│  │  ████ s5                      │  needs 6 > pool 5  │   (hard RED line)     │ │     stamp at the breach (LAW 7)
│  │  ████ s4                      └───────────────────┘                       │ │  STAMP text verbatim:
│  │  ████ s3                                                                   │ │  "INFEASIBLE · needs 6 > pool 5"
│  │  ████ s2   (teal = funded & fits)                                         │ │  teal blocks below line = funded
│  │  ████ s1                                                                   │ │  red block above = over capacity
│  │   the 6th block is RED — it pushed demand over the line                    │ │
│  │  (o══════════════════════o)   review pool h        5   distinct sinks: 6   │ │  ← same h slider governs the wall
│  │  Plain words: the ratchet only ever ADDS budget and never frees it, so as  │ │  ← GLOSS inline (LAW 5)
│  │  soon as more than h different agents have each been the weakest link, it  │ │
│  │  is trying to hold more than the pool can ever contain.                    │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

------------------ ▣ See the theory: misses vs pool size h — EXPANDED -----------
Reveal only (LAW 6). TWO distinct objects: the finite-sample LIVE anchors the
empirical dots land on, and the H_h asymptote the curve only reaches as the
stream lengthens. LRU climbs ~h (linear); MARKER climbs ~H_h (the harmonic
number, ~ln h) ASYMPTOTICALLY — its worst-case-competitive guarantee.

┌──────────────────────────────────────────────────────────────────────────────┐
│  ▼ See the theory: misses vs pool size h  ──────────────────── <details> open │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │   competitive ratio (× oracle)                                            │ │  ← SECONDARY analytic chart
│  │ 8┤                                              ╱● LRU ~ h (linear)        │ │  LRU = the ~h diagonal (red-ish)
│  │  │                                          ╱··                           │ │  ·· = LIVE LRU anchors (lands on)
│  │ 6┤                                      ╱·8:7.88                          │ │     {2:1.997,3:2.985,4:3.976,
│  │  │                                  ╱·6:5.93                              │ │      6:5.932,8:7.877}
│  │ 4┤                          ╱··4:3.98                                     │ │
│  │  │                  ╱··3:2.99                                             │ │  MARKER = the flat ~ln h curve.
│  │ 2┤·· ·· ·· ●━━━━━━━━━━━━━━━━━━━━━━━━━━●  MARKER (LIVE) → H_h asymptote     │ │  ·· = LIVE MARKER anchors (lands
│  │  │  2:1.997  4:2.06   8:2.68   16:3.28  32:3.88 ← live finite-sample      │ │      on at rounds=400):
│  │  │           - - -  H_h: 2.08 / 2.72 / 3.38 / 4.06  (dashed asymptote ↑)  │ │      {4:2.064,8:2.684,16:3.283,
│  │ 1┤- - - - - - - - - - - - - - - - - - - - oracle floor (dashed-grey)      │ │       32:3.878}
│  │   └──┬────────┬────────┬────────┬────────┬─────────────────────────       │ │  H_h asymptote (GHOST, dashed):
│  │   small pool ←      review pool h       → large pool                       │ │     {4:2.083,8:2.718,16:3.381,
│  │  the LIVE dots land on the finite-sample anchors; they creep UP toward     │ │      32:4.059} — reached only as
│  │  the dashed H_h asymptote as you lengthen the stream (never overshoot it)  │ │      rounds → ∞.
│  │  Plain words: drop-longest-ago gets linearly worse as the pool grows; the  │ │  DASHED-GREY = oracle floor 1.0
│  │  dice-roll policy stays near ln(h) — exponentially better — because there  │ │  ← "lengthen stream" probe note:
│  │  are several agents to randomize over (the harmonic number H_h ≈ ln h, the │ │     live curve CONVERGES to H_h,
│  │  policy's worst-case guarantee).                                          │ │     it is not pinned to it.
│  └──────────────────────────────────────────────────────────────────────────┘ │  ← GLOSS (LAW 5). H_h glossed as
└──────────────────────────────────────────────────────────────────────────────┘     "the harmonic number, about ln h"

   GLOSSES (inline, first use): "review pool = how many things you can watch at
   once" · "LRU = drop whatever you watched longest ago" · "MARKER = keep a
   coin-flip memory of what you've seen" · "clairvoyant / Belady = a cheater who
   already knows the future" · "H_h = the harmonic number, about ln h — MARKER's
   worst-case-competitive guarantee, an asymptote the live curve approaches"
   · "worst-case stream = a request order engineered to defeat the pool; on a
   typical workload both policies miss far less"

   ANCHOR-vs-LIVE NOTE (for builder): the empirical dots match the LIVE finite-
   sample anchors {2.06,2.68,3.28,3.88} at rounds=400 (mean over 8 seeds) — that
   is the |Δ| trust overlay. The H_h ticks {2.08,2.72,3.38,4.06} are the ASYMPTOTE
   and are drawn as a SEPARATE dashed reference; do NOT expect the live curve to
   sit on them (it lands just under, by design). (Aligns with the parity plan's
   convergence-band treatment for MARKER, not the 1e-6 contract used elsewhere.)


================================================================================
(3) tracking.html — the re-engineered VISIBLE-FAILURE Margin Wall
================================================================================

CUT-GATE honored AND re-based. The native "floor never prints 0.00" is GONE; the
backwards "Kalman breaches less" claim is also GONE (at the calibrated z both
policies sit at ~2% by construction). The 5-second story is now BAND THICKNESS:
a FAT amber deadband band beside a THIN teal Kalman band — "same safety, 3.2×
more wasted holding" — with both bands bottoming out ON one DRAWN margin-floor
wall (z·√P* = 0.127), and the floor card locked "can't go lower". Red breaches
remain as secondary texture, NOT as a count claim.

┌──────────────────────────────────────────────────────────────────────────────┐
│  How big a safety margin must you hold when you can't see the truth?  <h1>     │
│  You can't see the true required budget, only a noisy drifting signal. Kalman   │ <p class="lede">
│  and a naive deadband run on the SAME stream — watch how much fatter the        │
│  deadband's safety margin is for the SAME protection.                           │
│                                                                                │
│  ┌── headline strip ──────────────────────────────── .banner (amber bg) ─────┐│  ← LAW 2 + 3
│  │  Same safety, 3.2× more wasted holding: the naive deadband carries a much  ││  HEADLINE WORDS (verbatim):
│  │  fatter margin than the filter — and no policy reaches the noise floor.    ││  "Same safety, 3.2× more wasted
│  │  margin in words: how much extra budget you must hold above your guess     ││   holding: the naive deadband
│  └───────────────────────────────────────────────────────────────────────────┘│   carries a much fatter margin
│                                                                                │   than the filter — and no policy
│   required budget (true vs held — FAT amber band vs THIN teal band)   <svg>    │   reaches the noise floor."
│  ●┤░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  amber deadband band │  ← BAND THICKNESS is the story.
│   │░░░░░░░░░░░░░░░░░░░ z·σ = 0.411 (3.2× fatter, pure waste) ░░░░░░░░░░░░░░░░░░  │  AMBER band = deadband margin
│   │░░░░░░┊R┊░░░░░░░░░░░░░░░┊R┊░░░░░░░░░░░░░░░░░┊R┊░░░░░░░░░░░  (rare red = breach) │  z·σ — wide overhead, SAME 2%
│   │━━━━━━┃━━━━━━━━━━━━━━━━━┃━━━━━━━━━━━━━━━━━━━┃━━━━━━━━━━━━  true line (blue)    │  breach rate as Kalman.
│   │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ z·√P* = 0.127 (thin) ▓▓▓▓▓▓▓▓▓▓▓┊r┊▓▓  Kalman band (teal) │  BLUE = the true required budget
│   │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  (rare red r = breach) │  TEAL = Kalman held margin, thin
│  ──┼─────────────────────────────────────────────────────────────────────── │  R/r (red) = a breach step on
│   ▒▒▒▒▒▒▒▒▒▒ noise floor (smallest margin any filter can hold) z·√P* ▒▒▒▒▒▒▒▒  │  EITHER policy — both ~2%, so this
│   │  the thin teal band bottoms out ON this wall as ν→0 — can't go under it    │  is texture, not a count claim.
│   └──┬─────────┬─────────┬─────────┬─────────┬──────────────────────────────  │  ← DRAWN noise-floor WALL (LAW 7)
│    time →  (same stream, same seed, both policies)                            │     drawn at z·√P* = 0.127 — the
│                                                                                │     SAME quantity the teal band
│  (o═══════════════════════════════════════o)   drift speed ν                  │     rests on (commensurable units).
│   ↑ ONE slider · drift speed = how fast the true budget wanders   0.02         │  ← THE ONE VISIBLE SLIDER (.sl)
│                                                                                │     LAW 1 + GLOSS (LAW 5)
│  ┌─ STORY CARD ─ .card ──────────────┐  ┌─ details row ─ .muted (small) ─────┐ │  ← LAW 4
│  │ noise floor 0.127   🔒 can't go   │  │ Kalman margin z·√P* = 0.127       │ │  STORY-CARD LABEL (verbatim):
│  │ lower               .card .v      │  │ deadband margin z·σ = 0.411       │ │  v: "noise floor 0.127" (= z·√P*,
│  │ smallest margin any filter can    │  │  (3.2× fatter for the SAME 98%    │ │     the SAME number as the wall)
│  │ hold                .card .l      │  │   safety) · penalty √(σ/ν) = 3.16 │ │  l: "🔒 can't go lower · smallest
│  └───────────────────────────────────┘  └────────────────────────────────────┘ │      margin any filter can hold"
│                                                                                │  LOCKED with "can't go lower" 🔒
│  ▣ See the theory: margin floor vs drift speed ν  ────────── <details> closed │  stamp (mirrors INFEASIBLE wall).
│                                                                                │  NOTE: card shows z·√P*=0.127, NOT
│  on-widget legend: ━ true line (blue)  ▓ Kalman margin (teal, thin)            │  √(νσ)=0.063 — the band rests on
│      ░ deadband margin (amber, fat)  R/r breach (red, both ~2%)  ▒ noise floor │  0.127, so the card and the wall
│  Computed live by adaptive-online.js (tracking.py port), |Δ|<1e-6 vs parity test.   │  must agree at 0.127.
└──────────────────────────────────────────────────────────────────────────────┘  ← color legend ON widget (LAW 8)
                                                                                    ← .foot · FILE NAMES ONLY

   ONE visible slider .................. drift speed ν (.sl)
   "More controls" holds ............... observation noise σ · feasibility level
                                         z (target infeasibility %) · stream
                                         length · seed
   color legend ........................ blue=true line · teal=Kalman margin
                                         (thin) · amber=deadband margin (fat) ·
                                         red=breach · ▒/dashed-grey=noise floor z·√P*
   FUTURE-PROOFS THE SLIDER ............ every drawn tracking quantity is derived
                                         from √P* (kalmanSteadystateVar(ν,σ)); as
                                         ν moves, the floor line / card (z·√P*) stay
                                         exactly on the band. √(νσ) is used ONLY as
                                         the stated Ω(·) ORDER in the theory reveal,
                                         never as a drawn line or card number.

------------------ ▣ See the theory: margin floor vs ν — EXPANDED ----------------
Reveal only (LAW 6). As ν→0 the Kalman floor z·√P* sinks toward its irreducible
ORDER √(νσ) but the deadband z·σ stays fat — the margin bottoms out, never
collapses to 0. Here (and ONLY here) √(νσ) appears, as a lower dashed reference.

┌──────────────────────────────────────────────────────────────────────────────┐
│  ▼ See the theory: margin floor vs drift speed ν  ──────────── <details> open │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │   per-step safety margin you must hold                                    │ │  ← axis label IN WORDS (LAW 5)
│  │.4┤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ deadband z·σ (amber, stays fat)│ │  AMBER = deadband, ν-independent
│  │  │                                                       0.411 →           │ │
│  │.3┤                                        ╱                               │ │
│  │  │                                    ╱                                   │ │  TEAL = Kalman floor z·√P*, the
│  │.2┤                              ╱                                         │ │  SAME quantity as the cold-open
│  │  │                       ╱                                                │ │  wall; sinks as ν→0 …
│  │.13┤             ╱──── Kalman z·√P* (teal)   ● = current ν → 0.127         │ │
│  │  │       ╱                                                                │ │  … toward the irreducible ORDER
│  │.06┤▒▒▒●▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ irreducible order √(νσ) = 0.063 (dashed) │ │  √(νσ)=0.063 (a SEPARATE, lower
│  │ 0┤ ← margin never reaches 0                                              │ │  dashed reference — NOT the
│  │   └──┬────────┬────────┬────────┬────────┬─────────────────────────       │ │  cold-open wall, which is 0.127)
│  │   slow drift ←      drift speed ν      → fast drift                         │ │
│  │  Plain words: filtering shrinks the margin you must hold to z·√P* (0.127   │ │  ← GLOSS (LAW 5)
│  │  here), but observation noise plus drift leave an irreducible floor of     │ │  Two clearly separated lines:
│  │  ORDER √(νσ) (≈0.063) that no causal filter beats. The deadband ignores    │ │  the operating margin z·√P*=0.127
│  │  all this and over-holds at z·σ = 0.411 — a factor √(σ/ν) ≈ 3.16 wasted.   │ │  (teal, = the wall) and the Ω(·)
│  └──────────────────────────────────────────────────────────────────────────┘ │  scaling √(νσ)=0.063 (dashed).
└──────────────────────────────────────────────────────────────────────────────┘

   GLOSSES (inline, first use): "drift speed ν = how fast the true budget wanders"
   · "deadband = hold a fixed fat margin, no filtering" · "Kalman = the best
   causal filter for a wandering signal under noise" · "noise floor z·√P* = the
   smallest margin any filter can hold at this drift — the band bottoms out on it"
   · "irreducible order √(νσ) = how that floor SHRINKS as drift slows; it never
   reaches 0 for ν > 0 (theory reveal only)"

   CUT-GATE NOTE (for builder): the 5-second story is the FAT-vs-THIN band gap
   ("same safety, 3.2× more wasted holding"), NOT a breach count — at the
   calibrated z=2.054 BOTH policies breach ≈2% by construction (deadband 1.93%,
   Kalman 2.04%), so red flashes are a SPECKLE (~2 per ~120-step window each),
   not a wall, and the deadband does NOT breach more. Ship ONLY if the band-
   thickness gap + drawn floor wall read as the failure in <5s. If you instead
   want red to genuinely SPRAY, the only honest way is to add (behind More
   controls) a DELIBERATELY under-margined naive policy (margin << z·σ) so its
   breaches are real while Kalman stays clean — and re-run the CUT-GATE on THAT.
   Do NOT show fixed breach integers as canonical anchors; if shown at all, frame
   them live as "this run" and reflect that both sit at ~2% by design. The only
   anchored tracking numbers are the margins (z·√P*=0.127, z·σ=0.411) and the
   penalty (3.16). If neither framing reads as failure in <5s, this becomes a
   paper figure, not a widget.


================================================================================
(4) index.html — "Online oversight controllers" section (attract-loop)
================================================================================

Section appended below the existing 7-card grid. OVERSIZED auto-playing ski-rental
hero card (30s loop, freezes at the fork, respects prefers-reduced-motion), then
caching + tracking cards. Sequence-framing copy written out.

┌──────────────────────────────────────────────────────────────────────────────┐
│  Online oversight controllers                                       <h2>      │  ← neutral title (no author/venue)
│  The cockpit showed WHAT to allocate at rest. These three show WHEN to hold,   │ <p class="lede"> — SEQUENCE-FRAMING
│  release, and evict as things change.                                          │   COPY (verbatim, spec wording)
│                                                                                │
│  ┌─ OVERSIZED HERO CARD · .card border:2px teal · auto-plays ────────────────┐│  ← attract-loop, S effort,
│  │  ┌── live mini headline ─ .banner ─────────────────────────────────────┐  ││     pure presentation over
│  │  │  bounded vs unbounded                                               │  ││     adaptive-online.js
│  │  └─────────────────────────────────────────────────────────────────────┘  ││  freeze-frame stamp text:
│  │   review held (× best-possible)                          ┌─ stamp ─────┐  ││  "unbounded · 14.9× and rising"
│  │  ╱ (ratchet escapes, RED)  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ unbounded   │  ││  (uses the SAME 14.9× rendered
│  │ ╱━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ 14.9× and   │  ││   number as the standalone hero —
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.88 2λ ctlr  └─ rising ────┘  ││   consistency is load-bearing)
│  │  - - - - - - - - - - - - - - - - - - - - 1.0 clairvoyant (dashed)         ││  TEAL flat ctlr (1.88, LIVE) vs
│  │                                                                          ││  RED escaping ratchet — the killer
│  │            ╭──────────────────────╮                                      ││  fork, auto-swept, zero interaction
│  │            │   now you try →       │   ← fades in after the sweep freezes ││  after freeze, fade in:
│  │            ╰──────────────────────╯                                      ││  "now you try →"  (hand-over
│  │  Ski-Rental Duty Sweep — hold or release a recovered agent's budget       ││   AFTER the hook)
│  └───────────────────────────────────────────────────────────────────────────┘│  → links to skirental.html
│                                                                                │
│  ┌─ .grid (2-up) ────────────────────────────────────────────────────────────┐│  ← caching + tracking cards
│  │ ┌─ .card ──────────────────────┐  ┌─ .card ──────────────────────────────┐ ││
│  │ │ Cache Eviction Race          │  │ Tracking: the Margin Wall            │ ││
│  │ │ ✗red miss / ●teal hit · two  │  │ ━blue true line · ▓thin teal vs ░fat │ ││  static teaser thumbnails,
│  │ │ policies race for finite     │  │ amber margins — same safety, 3.2×    │ ││  the live contrast on each
│  │ │ review slots — which agent   │  │ more wasted holding; bands bottom    │ ││
│  │ │ do you cut? → caching.html   │  │ out on the noise floor. → tracking.html│ ││  → link to each widget
│  │ └──────────────────────────────┘  └──────────────────────────────────────┘ ││
│  └───────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│  Every number computed live by adaptive-online.js, pinned to the Python modules     │  ← .foot · FILE NAMES ONLY
│  by the parity test (|Δ|<1e-6).                                                 │
└──────────────────────────────────────────────────────────────────────────────┘

   classes used ........................ .card (hero border:2px teal; two teasers)
                                         · .grid (2-up teaser row) · .banner
                                         (mini headline) · .lede (sequence copy)
                                         · .foot
   attract-loop discipline ............. auto-sweep · freeze at fork · stamp
                                         "unbounded · 14.9× and rising" · THEN
                                         "now you try →" · honors prefers-reduced-
                                         motion (static freeze-frame, no motion)
   color legend (shared, LAW 8) ........ teal=2λ ctlr/hit · red=ratchet/miss ·
                                         blue=true line · amber=deadband ·
                                         dashed-grey=clairvoyant/floor
   number consistency (load-bearing) ... the hero card stamps the SAME 14.9× the
                                         standalone widget renders; the teal flat
                                         line sits at the SAME 1.88 LIVE value.
   page-string note (for builder) ...... the NEW section ships zero author/venue/
                                         repo strings. Pre-existing index.html
                                         strings (header credit L11, GitHub/pip
                                         L23) are INTENTIONALLY retained for the
                                         public repo and are out of scope for this
                                         section; a scrub step is needed ONLY for a
                                         blind-paper screenshot build (per spec).


================================================================================
(5) cockpit.html — "Static | Online" capstone panel
================================================================================

Promotes the existing inert per-node `drift` field (keyed `drift:` on each node
template, e.g. `llm:{...,drift:0.12}`) into the driver of a `.seg` Static|Online
toggle. Reuses the requestAnimationFrame token clock and `delivered_quality = min
over sinks` from mso-core.analyzePipeline (not re-derived). Online mode adds:
moving red bottleneck dot, per-sink budget bars (amber held vs required tick),
pool occupancy vs the h cap. Needs 1–2 multi-sink templates.

┌──────────────────────────────────────────────────────────────────────────────┐
│  toolbar (existing): [Load template ▾] [Quality target o─] … [▶ Run tokens]    │
│  NEW, in toolbar:    Mode  ┌────────┬────────┐                                 │  ← .seg toggle (matches existing
│                            │ Static │ Online │   ← .seg (Static = default .on) │     zoom .seg idiom)
│                            └────────┴────────┘                                 │  default Static = current cockpit
│  ┌─────────────────────────┬──────────────────────────┬─────────────────────┐ │
│  │ palette (unchanged)     │  canvas (node graph)      │ panel               │ │
│  │                         │                           │                     │ │
│  │  Generate               │   ┌─────┐                 │ ┌ headline .banner ┐│ │  ← LAW 2 (Online mode):
│  │  ● LLM drafter          │   │intent│──┐              │ │ Online · bottleneck││ │  "Online · the bottleneck is
│  │  ● Extractor            │   └─────┘  │   ┌──────┐    │ │ moving under drift ││ │   moving under drift"
│  │  …                      │           ├──▶│ reco │●red │ └──────────────────┘│ │  ●red = moving bottleneck dot
│  │  Govern                 │   ┌─────┐  │   └──────┘ ↑  │                     │ │  (reuses existing cx:W-9,cy:8,r:4
│  │  ● Model reviewer       │   │search│─┘    bottleneck │ ┌ per-sink budgets ┐│ │   fill #E24B4A circle idiom)
│  │  …                      │   └─────┘      dot walks   │ │ reco  [▓▓▓▓░|·]  ││ │
│  │                         │      ┌──────┐   the sinks  │ │ pay   [▓▓░░░|· ] ││ │  ← per-sink .bar: amber ▓ = held,
│  │  (multi-sink template   │      │ pay  │●  under drift│ │ ship  [▓▓▓▓▓|·]  ││ │     | = required tick, teal when
│  │   so bottleneck has     │      └──────┘              │ │ amber=held · |req ││ │     held ≥ required, red if under
│  │   somewhere to move)    │   ┌──────┐                 │ └──────────────────┘│ │
│  │                         │   │ ship │● (3 sinks)      │ ┌ pool occupancy ──┐│ │  ← pool occupancy vs h cap
│  │                         │   └──────┘                 │ │[████████░░] 3/4  ││ │     .bar filled to funded count;
│  │                         │                            │ │ funded vs pool h ││ │     hard line at h
│  │                         │  ●teal hold · ●red release │ │ ═══ h cap ═══    ││ │  hold/release events fire on graph
│  │                         │   events fire here         │ └──────────────────┘│ │  (teal pulse hold, red pulse release)
│  │                         │                            │ ┌ Theory toolkit ──┐│ │  ← readouts in EXISTING
│  │                         │                            │ │ dwell* = 2λ       ││ │     theory-readout/recipes panel
│  │                         │                            │ │ pool h = ⌊C/b*⌋=4 ││ │     (not a new panel)
│  │                         │                            │ │ delivered = min   ││ │  delivered_quality = min over
│  │                         │                            │ │   over sinks (reuse)│ │   sinks — REUSED from
│  │                         │                            │ └──────────────────┘│ │   mso-core.analyzePipeline
│  └─────────────────────────┴──────────────────────────┴─────────────────────┘ │
│                                                                                │
│  Static|Online via adaptive-online.js + the inert per-node drift field; pool & dwell│  ← .foot addition · FILE NAMES ONLY
│  pinned to the Python modules by the parity test (|Δ|<1e-6).                    │
└──────────────────────────────────────────────────────────────────────────────┘

   ONE primary control (this panel) .... the .seg Static|Online toggle
        (NB: the cockpit is the flagship multi-control surface by design; the
         capstone adds exactly ONE new control — the mode toggle — and reuses
         the existing Quality-target / drift sliders rather than adding knobs.)
   "More controls" / reuse ............. per-node Drift rate already lives on each
                                         node template, keyed `drift:` (the inert
                                         field, e.g. llm:{...,drift:0.12}); it drives
                                         the motion — no new slider added.
   what Online mode animates ........... ●red moving bottleneck dot · per-sink
                                         budget bars (amber held vs required
                                         tick) · pool occupancy bar vs h cap ·
                                         hold(teal)/release(red) event pulses
   headline strip (Online) ............. "Online · the bottleneck is moving under
                                         drift" (.banner)
   color legend (LAW 8, shared) ........ teal=held/funded/hold-event · amber=
                                         budget held · red=bottleneck/release/
                                         over-cap · dashed-grey=h cap line
   templates needed .................... 1–2 purpose-built MULTI-SINK templates
                                         (current templates are single-sink
                                         chains → bottleneck can't move)
   page-string note (for builder) ...... the NEW Online wiring ships clean; the
                                         pre-existing cockpit footer string
                                         (package version, L131) is INTENTIONALLY
                                         retained for the public repo and is out of
                                         scope here — scrub only for a blind build.

================================================================================
DESIGN-LAW COMPLIANCE (all five surfaces)
================================================================================
  LAW 1  one visible slider ... skirental:slack duty · caching:pool h ·
         tracking:drift ν · index:none(auto) · cockpit:one .seg toggle. Every
         other knob behind ▣ "More controls"/"Advanced".
  LAW 2  headline strip ....... .banner above every chart, plain-language outcome.
  LAW 3  direction on number .. "1.0 = matches a perfect oracle · higher = worse"
         on skirental/caching headline + cards; tracking floor "can't go lower".
  LAW 4  one story card ....... .card .v big number + .card .l label; the
         worst-case bound 1.95 (ski-rental), Belady, penalty 3.16, and z·σ demoted
         to the .muted details row. Cards show the LIVE realized values (ski-rental
         1.88, tracking floor 0.127), never a bound dressed as the realized cost.
  LAW 5  jargon glossed ....... inline at first use; axis labels in words
         ("safety margin you must hold", "review pool = how many you can watch");
         every competitive-ratio gloss carries the "worst-case / against an
         adversary" qualifier at first use.
  LAW 6  theory is a REVEAL ... U-curve, CR-vs-h (+ H_h asymptote), floor-vs-ν
         (+ √(νσ) order line), ratchet wall all inside <details>, never cold-open.
  LAW 7  let it run off-frame . skirental ratchet "unbounded · 14.9×" stamp ·
         caching "INFEASIBLE" wall · tracking drawn margin-floor wall (z·√P*=0.127)
         the thin band rests ON + locked card. No axis auto-rescale to contain
         failure. Floor LINE and floor CARD are the SAME commensurable quantity.
  LAW 8  locked color semantics teal=feasible/held/hit/funded · amber=margin/
         holding · red=refund/miss/infeasible/breach · blue=online estimate ·
         dashed-grey=offline optimum/analytic floor (incl. the 1.95 ski-rental
         bound ghost, the H_h asymptote, and the √(νσ) order line). Identical
         across all 5.
  ANON   Masking A/B is OUT OF SCOPE for this showcase — no widget or flow ships
         (the spec's deliverables list 1–7 contains no masking surface; it is named
         only as an anonymization GUARD on adaptive-online.js). No author/venue/repo
         strings in any NEW artifact; benchmark values appear only as faint ··
         anchor ticks (the LIVE values; bounds/asymptotes are separate dashed-grey
         ghosts). If a masking surface is ever added later, it MUST keep "Agent A"/
         "Agent B" as bare numbers computed live via mso-core.sigmaCorrFixedPoint +
         maskingIndex (A: σ_raw 0.07, catch 0.125 → p=0.186, M*=2.7; B: σ_raw 0.028,
         catch 0.206 → p=0.228, M*≈8.1) and MUST NOT import mso-registry.js /
         mso-priors.js (which carry real vendor model names). masking.html already
         demonstrates this live-compute-no-registry path.
```

Wireframe document complete. All five surfaces are delivered as annotated monospace box sketches obeying the 8 design laws.

Key fidelity notes for the implementers who consume this:
- **Source files mirrored** (absolute paths): the SVG `<polyline>` time-series idiom from `web/widgets/return-operator.html`; the absolute-positioned teal/red `.bar` from `web/widgets/waterfilling.html`; the red bottleneck dot (`<circle cx=W-9 cy=8 r=4 fill="#E24B4A">`), the `requestAnimationFrame` token clock (`simLoop`/`simOn`/`simLast`), the inert per-node `drift` field (keyed `drift:`, node templates), and the `.seg` toggle from `web/widgets/cockpit.html`; the `.card .l/.v` + `.banner` + `.foot` structures from `web/theme.css`.
- **LIVE vs GHOST discipline** (load-bearing for the anchor-vs-live trust overlay): the rendered curve always lands on the LIVE value (ski-rental full-instance CR **1.88**; caching finite-sample MARKER {2.06,2.68,3.28,3.88}; tracking floor **z·√P*=0.127**). Proven bounds/asymptotes are drawn as SEPARATE dashed-grey ghosts the live curve approaches but never sits on (ski-rental worst-case bound **1.95** = 2−1/(2λ); caching H_h asymptote {2.08,2.72,3.38,4.06}; tracking irreducible order **√(νσ)=0.063**).
- **Tracking re-engineered** to the only honest <5s story — fat-vs-thin band thickness ("same safety, 3.2× more wasted holding"), with the floor line and floor card both at the commensurable z·√P*=0.127 the band rests on; breach counts dropped (both policies sit at ~2% by construction); cut-gate restated against this revised framing.
- **One rendered ratchet number** (14.9×) used verbatim in the headline strip, on-frame stamp, anchor tick, and index card.
- **Anonymization**: Masking A/B explicitly OUT OF SCOPE; no author/venue/repo strings in new artifacts; pre-existing page strings flagged as intentionally retained for the public repo.

CHANGELOG: Applied all four blockers/relevant findings and every major finding. (1) TRACKING floor blocker: relabelled the drawn floor wall and locked story card from the wrong √(νσ)=0.063 to the correct commensurable z·√P*=0.127 (= `noise_floor_per_step`, verified live), the exact quantity the teal Kalman margin band bottoms out on; demoted √(νσ)=0.063 to a separate lower dashed "irreducible order" line in the theory reveal only; updated the legend to "noise floor z·√P*" and derived every tracking quantity from √P*/`kalmanSteadystateVar` so the slider stays correct. (2) TRACKING visible-failure blocker: re-based the cold-open from the false "Kalman breaches less" claim to the true fat-vs-thin band-thickness story ("same safety, 3.2× more wasted holding", deadband z·σ=0.411 vs Kalman z·√P*=0.127), deleted the fabricated "breaches 6×/9×" integers (both policies sit at ≈2% by construction — verified deadband 1.93% / Kalman 2.04%), kept red breaches as secondary texture, and rewrote the cut-gate note against the revised framing with the deliberately-under-margined fallback. (3) Ski-rental hero major: disambiguated the LIVE full-instance ratio (1.88, verified from `dwell_cost/opt_cost`) on the flat teal line and card from the proven worst-case bound 2−1/(2λ)=1.95, which is now a dashed-grey ghost tick + details-row label ("can approach, never cross"), no longer dressed as the realized cost. (4) Caching cross major: split the LIVE finite-sample MARKER anchors {2.06,2.68,3.28,3.88} (rounds=400, 8-seed mean, what the empirical dots land on) from the H_h asymptote {2.08,2.72,3.38,4.06} (a separate dashed reference the curve only approaches as rounds→∞), with a builder anchor-vs-live note; refreshed LRU anchors to the exact computed values and framed MARKER as O(log h)/~H_h asymptotically. (5) Ratchet-number consistency minor: pinned ONE rendered value 14.9× (verified live at τ=320/duty≈0.003) across the post-probe headline, on-frame stamp, anchor tick, and index card. (6) Worst-case-qualifier minor: added "worst-case / against an adversary" to every competitive-ratio gloss and headline (caching headline, U-curve title, glosses) while leaving ski-rental's correct "never more than 2×". (7) Masking scope minor: declared Masking A/B explicitly OUT OF SCOPE (absent from the spec's deliverables 1–7), dropped the "if surfaced" hedge, and kept the bare-numbers/no-registry guard as a conditional for any future addition (verified A p=0.186/M*=2.7, B p=0.228/M*≈8.1 via mso-core math). (8) drift-field nit: corrected `drift_rate` to the actual field name `drift` (keyed `drift:` on node templates, e.g. `llm:{...,drift:0.12}`, L144-178) in the cockpit mock. (9) Page-string nit: added per-surface builder notes that pre-existing index.html/cockpit page strings are intentionally retained for the public build and out of scope. Added a top-of-document VERIFIED-NUMBERS block codifying the LIVE-vs-GHOST split; preserved the full structure, richness, and all annotations. Final written to /Users/crbazevedo/Documents/papers/minimal-oversight-project/delegation-lab/design/online-cockpit/02-lowfi-mocks.md.

