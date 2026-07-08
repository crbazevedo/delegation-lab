# LAYER 3 — FRONT-END PLAN: Adaptive review cockpit showcase

Single source of truth for WHAT: `delegation-lab/COCKPIT_ONLINE_SHOWCASE.md`. This plan is what an engineer implements from. All paths are repo-relative to `delegation-lab/`.

**Math source of truth — read this carefully, it is load-bearing:**

| Module | Importable package (parity reference) | Per-instance forms the hero/race drive |
|---|---|---|
| Ski-rental | `src/minimal_oversight/skirental.py` — per-slack-phase helpers only (`skirental_dwell`, `skirental_ratio`, `opt_slack_cost`, `dwell_slack_cost`, `worst_case_ratio`, `minimax_dwell`). | **`scripts/online_skirental.py`** — the **full-instance** closed forms (`required`, `opt_cost`, `dwell_cost`) and the ratchet cost (an inline branch of `run("ratchet", …)` + `cost(...)`; **there is no standalone `ratchet_cost()` symbol**). These produce the hero's 14.9 / 1.95 numbers and live ONLY in the script. |
| Tracking | `src/minimal_oversight/tracking.py` — `kalman_steadystate_var`, `matched_margin`, `noise_floor_per_step`, `deadband_margin`, `KalmanTracker`. | `scripts/online_tracking.py` only as the source of the fixed observation stream (`simulate`) for the trajectory fixture. |
| Caching | `src/minimal_oversight/caching.py` — `pool_capacity`, `belady_misses`, `lru_misses`, `marker_misses(…, seed=0)`, `ratchet_demand`, `competitive_ratio`, `cyclic_adversary`, `SharedPoolController`. | `scripts/online_caching.py` only as the source of the H_h convergence-harness pattern (`test_c3`: `rounds=400`, `seed∈range(8)`). Its symbols differ (`ratchet_capacity`, `cyclic`, no default seed) — **do not import them.** |

> **Critical build dependency (do not skip).** `scripts/` has **no `__init__.py`** and is not imported by `tests/test_parity.py` today. The ski-rental full-instance forms therefore are not yet a package API — `hasattr(minimal_oversight.skirental, "opt_cost")` is `False`. Before the ski-rental parity fixture can exist, the Python side of `online_parity_runner.js` must load `scripts/online_skirental.py` via `importlib.util.spec_from_file_location` (or add `scripts/__init__.py` + `sys.path`). There must be a Python reference for `adaptive-online.js`'s `ratchetCost`/`optCost`/`dwellCost`/`requiredSeq` to pin to at `1e-6`, or fixture 1 cannot be written.

The product: three standalone widgets (ski-rental hero, caching, tracking) + an index attract-loop + a cockpit "Online" capstone, all powered by one new UMD module `web/adaptive-online.js` (a literal port of the Python), gated by `tests/test_parity.py` at `|Δ| < 1e-6`. The eight design laws are load-bearing and called out per artifact below.

**Hero operating point — pinned once, used everywhere (resolves the 14.9-vs-0.003 inconsistency).** The hero instance is `W=1, λ=10, ncyc=20`. The slider's extreme is **`τ = 320`**, i.e. **duty `= 1/(1+320) = 0.0031`** (display as "≈0.003"). At `τ=320` the live ratchet ratio recomputes to **14.92**, landing the curve exactly on the published **14.9** anchor tick; the `dwell@2λ` line sits at `skirentalRatio(10) = 1.95` (the proven worst-case bound), hugging the dashed `1.0` clairvoyant floor. **Do not use `τ=332`:** the exact closed forms give ratchet ratio **15.48** there, which would either fail the parity gate written as `≈14.9` or silently corrupt the headline. Every stamp, anchor, and gate below uses `τ=320 → 14.9`. (`ncyc` matters too — 15.1 at `ncyc=10`, 15.7 at `ncyc=40` for the same `τ` — so it is pinned at 20 in the contract.)

---

## (a) `web/adaptive-online.js` — UMD API

Same UMD **code wrapper** as `web/mso-core.js` (lines 16–19): `module.exports` under Node, `root.AdaptiveOnline` in the browser. Mirror **only the IIFE + return shape** — **not** the reference/author header comment. `mso-core.js`'s header (line 10–11) carries `"Minimal Oversight … (Azevedo, 2026)"`; copying it verbatim would import an author/venue string into a new artifact and break the "zero author/venue/repo strings" guardrail. The `adaptive-online.js` header carries **only** a neutral functional description plus the parity-pinned note — no author, venue, arXiv, or repo string.

**It MUST NOT `require` `mso-registry.js` or `mso-priors.js`** (anonymization guardrail — those carry vendor model names). Pure math + the two stateful classes only. `"use strict"`, no external deps (port the NumPy RNG by hand; see caching note).

```js
/**
 * adaptive-online.js — browser port of the online oversight-controller math
 * (ski-rental release, Kalman tracking, shared-pool caching). Every function
 * is pinned to its Python reference by tests/test_parity.py (|Δ| < 1e-6):
 * skirental/tracking exactly, caching deterministically + MARKER by convergence.
 * No external deps; do not import the registry/priors modules.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.AdaptiveOnline = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  // ... functions below ...
  return { /* all exports */ };
});
```

Units convention across the module: budgets/margins are in units of `b*` (peak required budget; `BSTAR = 1.0` in `scripts/online_skirental.py` line 41, so `b` defaults to `1.0`). `lam` (λ) is the switching half-cost in steps. Ratios are dimensionless (1.0 = clairvoyant-optimal). Misses are integer counts. Variances are in `b*²`.

### Ski-rental — per-slack-phase helpers (port of `src/minimal_oversight/skirental.py`)

| JS signature | Returns | Mirrors (`skirental.py`) | Notes |
|---|---|---|---|
| `skirentalDwell(lam)` | `number` (steps) | `skirental_dwell` (L23) | `2*lam`. The break-even dwell. |
| `skirentalRatio(lam)` | `number` (ratio) | `skirental_ratio` (L29) | `2 - 1/(2*lam)`. The proven **worst-case** competitive bound — the dashed-grey ghost line. |
| `optSlackCost(tau, lam, b=1.0)` | `number` (cost) | `opt_slack_cost` (L34) | `b*min(tau, 2*lam)`. Clairvoyant per-slack-phase cost. |
| `dwellSlackCost(tau, lam, d, b=1.0)` | `number` (cost) | `dwell_slack_cost` (L40) | `d<=tau` → `b*((d-1)+2*lam)`, else `b*tau`. |
| `worstCaseRatio(d, lam, tauMax=1000, b=1.0)` | `number` (ratio) | `worst_case_ratio` (L51) | `max over tau in [1,tauMax]` of `dwellSlackCost/optSlackCost`. The U-curve sample. |
| `minimaxDwell(lam, candidates=null, tauMax=1000)` | `[number, number]` `(dwell*, worstRatio)` | `minimax_dwell` (L59) | default candidates `sorted(unique([1, lam, 1.5*lam, 2*lam, 2.5*lam, 4*lam]))`. |

### Ski-rental — full-instance closed forms (port of `scripts/online_skirental.py`)

These are the lines the duty slider actually drives and that produce the 14.9 / 1.95 numbers. They live **only** in the script (see the build-dependency note above); add them to the same module so they are parity-pinned too.

| JS signature | Returns | Mirrors (`online_skirental.py`) | Notes |
|---|---|---|---|
| `requiredSeq(W, tau, ncyc, b=1.0)` | `number[]` (length `(W+tau)*ncyc + W`) | `required` (L45) | one-row instance; `[b×W, 0×tau]×ncyc + b×W`. |
| `optCost(W, tau, lam, ncyc, b=1.0)` | `number` (cost) | `opt_cost` (L108) | clairvoyant total. At the hero point `optCost(1,320,10,20) = 431`. |
| `dwellCost(W, tau, lam, ncyc, d, b=1.0)` | `number` (cost) | `dwell_cost` (L115) | dwell-`d` total; at `d=2*lam` this is the teal controller line. |
| `ratchetCost(W, tau, lam, ncyc, b=1.0)` | `number` (cost) | `run("ratchet", required(W,tau,ncyc), lam)` then `cost(h,sw,lam)` (L81–82, 97–98, 103) — **no standalone fn** | never-release: `holding = b*W*(ncyc+1) + b*tau*ncyc`, `switching = b` (one initial acquire), `cost = holding + lam*switching`. Verified `= 6431` at the hero point (`holding=6421, switching=1`). Diverges as `tau→∞` at fixed `W`. The red line that runs off-frame. |
| `dutyRatio(W, tau, lam, ncyc, policy)` | `number` (ratio vs opt) | `cr` (L127) | convenience: `policy∈{"ratchet","dwell@2lam"}` → `cost/optCost`. The number the headline prints. |

> **Hero contract:** the **one slider is `tau` (slack length)** displayed as **duty `= W/(W+tau)`** with `W=1, lam=10, ncyc=20`. The slider's far extreme is **`tau=320` (duty 0.0031, shown "≈0.003")**, where `ratchetCost/optCost` recomputes live to **14.92** → lands on the **14.9** anchor; `dwell@2lam` sits at `skirentalRatio(10)=1.95` (worst-case bound), hugging the dashed `1.0`. Do not let the slider reach `tau=332`. Anchor ticks: `skirentalRatio(lam)` at λ=1/5/10/20 → 1.50/1.90/1.95/1.975, all **worst-case** guarantees.

### Tracking — port of `src/minimal_oversight/tracking.py`

| JS signature | Returns | Mirrors (`tracking.py`) | Notes |
|---|---|---|---|
| `Z_DELTA_98` | `number` const `= 2.054` | `Z_DELTA_98` (L27) | exported const. |
| `kalmanSteadystateVar(nu, sigma)` | `number` (variance, `b*²`) | `kalman_steadystate_var` (L30) | positive Riccati root `(-q + sqrt(q²+4qr))/2`, `q=nu², r=sigma²`. |
| `matchedMargin(pStar, zDelta=2.054)` | `number` (margin, `b*`) | `matched_margin` (L37) | `zDelta*sqrt(pStar)`. |
| `noiseFloorPerStep(nu, sigma, zDelta=2.054)` | `number` (margin/step) | `noise_floor_per_step` (L43) | `matchedMargin(kalmanSteadystateVar(nu,sigma))`. **The "noise floor" line + locked card.** At the headline `(0.02,0.20)` this is `0.127`. |
| `deadbandMargin(sigma, zDelta=2.054)` | `number` (margin, `b*`) | `deadband_margin` (L49) | `zDelta*sigma`. The naive over-holding band. At `(0.02,0.20)` this is `0.411` — **3.24× fatter** than the Kalman margin for the **same** feasibility. |
| **`KalmanTracker(nu, sigma, xhat=0, varInit=NaN)`** | object | `KalmanTracker` (L55) | `varInit` NaN → `sigma²` (mirrors `__post_init__`, L71). Stateful — one obs/step. |
| `tracker.update(obs)` | `number` (xhat) | `.update` (L75) | exact predict/gain/update; mutates `this.xhat`, `this.var`. |
| `tracker.feasibleBudget(obs, zDelta=2.054)` | `number` (held budget) | `.feasible_budget` (L84) | calls `update(obs)`, returns `est + zDelta*sqrt(this.var)`. |

> Implement `KalmanTracker` as a constructor-function (or `class`) with public mutable `nu, sigma, xhat, var`. The widget runs the Kalman tracker and a fixed-margin deadband on the **same** observation stream — see §(e) for the re-engineered cold-open (band-thickness lead, not breach-count).

### Caching — port of `src/minimal_oversight/caching.py`

NumPy's `default_rng` is **not** byte-reproducible in JS. Port MARKER's randomness to **mulberry32** (`mso-sim.js` `makeRng`, L25–33) so browser==Node, and use the **same seed in the Node parity fixture** (compare the JS MARKER to the JS-in-Node MARKER for determinism, and to the H_h anchor for correctness — see Parity Plan §d). LRU/Belady/ratchet/cyclic are deterministic → exact integer parity to the package.

| JS signature | Returns | Mirrors (`caching.py`) | Notes |
|---|---|---|---|
| `poolCapacity(c, bStar)` | `int` | `pool_capacity` (L29) | `floor(c/bStar)`; throw if `bStar<=0`. |
| `beladyMisses(requests, h)` | `int` | `belady_misses` (L40) | offline optimum yardstick (the dashed number, not a lane). |
| `lruMisses(requests, h)` | `int` | `lru_misses` (L65) | Θ(h)-competitive (**worst-case**, on the cyclic adversary). |
| `markerMisses(requests, h, seed=0)` | `int` | `marker_misses` (L81), `seed=0` default | **mulberry32**, not NumPy. O(log h) **worst-case**. Default seed 0 matches the package signature. |
| `ratchetDemand(requests)` | `int` | `ratchet_demand` (L103) | distinct sinks ever requested; `> h` ⇒ INFEASIBLE. |
| `competitiveRatio(policy, requests, h, seed=0)` | `number` (ratio) | `competitive_ratio` (L109) | `'lru'|'marker'`; `on/belady`, `Infinity` if Belady=0. |
| `cyclicAdversary(h, rounds)` | `number[]` | `cyclic_adversary` (L121) | `h+1` distinct pages cycled. The race stream. |
| **`SharedPoolController(h, policy='lru', seed=0)`** | object | `SharedPoolController` (L128) | stateful pool; `policy∈{'lru','marker'}`. |
| `ctrl.request(sink)` | `{hit:boolean, miss:boolean}` | `.request` (L147) returns bare `True`=miss | **Return-shape note:** Python returns bare `True`=miss. JS returns `{hit:!miss, miss}` for the widget's teal-pulse/red-flash. Parity fixture compares the `miss` field only. |
| `ctrl.funded` | `number[]` (live) | `.funded` (L142) | the funded-slot lane state; drives the spotlight + INFEASIBLE stack. |
| `ctrl.misses` | `int` (live) | `.misses` | running re-fund count. |

> **Caching anchors — there are TWO distinct objects, do not conflate them (this is the anchor-vs-live trust contract):**
> 1. **The finite-sample anchor ticks the LIVE empirical curve lands on** (exact match at `rounds=400`, mean over 8 seeds): LRU `{2:1.99, 3:2.97, 4:3.95, 6:5.86, 8:7.76}`; MARKER `{4:2.06, 8:2.68, 16:3.28, 32:3.88}`. These are the faint ticks the dragged/lengthened live dots converge **onto**.
> 2. **The H_h asymptotic reference the curve only approaches as `rounds→∞`**: `H_h = Σ 1/i = {4:2.083, 8:2.718, 16:3.381, 32:4.059}`. This is a *separate* dashed asymptote, drawn **only** in the "see the theory" reveal.
>
> The finite-sample MARKER ticks sit **below** H_h (3.88 vs 4.06 at h=32). If the live curve were overlaid on the H_h line it would appear to *miss*. So: the live curve lands on object (1); the "see the theory" reveal plots object (2) as the dashed asymptote and labels MARKER as **O(log h) ~ H_h asymptotically (worst-case-competitive)**. LRU's `~h` anchors are the finite-sample values in (1); the `~h` law is the reveal's asymptote.

---

## (b) File tree — new / changed

```
delegation-lab/
├── web/
│   ├── adaptive-online.js                  NEW  UMD math port (window.AdaptiveOnline); load-bearing, build first
│   ├── index.html                     EDIT add "Online oversight controllers" section + auto-play hero card
│   └── widgets/
│       ├── skirental.html             NEW  HERO — duty sweep, two lines, one slider, overflow stamp
│       ├── caching.html               NEW  two-lane LRU-vs-MARKER spotlight race + ratchet wall
│       ├── tracking.html              NEW  Kalman-vs-deadband band-thickness story + noise-floor wall (CUT-GATE)
│       └── cockpit.html               EDIT add Static|Online toggle, animate drift, 1–2 multi-sink templates
├── scripts/
│   ├── online_parity_runner.js        NEW  Node harness: computes AdaptiveOnline outputs for shared inputs
│   │                                        (mirror of parity_runner.js; SEPARATE file to keep online deps out)
│   └── __init__.py                    NEW (optional) makes scripts/online_skirental.py importable for the fixture
│                                        — OR load it via importlib in the test (see §d); pick one, document it
├── tests/
│   └── test_parity.py                 EDIT add 3 online fixtures + finite-sample caching convergence check
└── mkdocs.yml                         EDIT nav: add the three widgets under a new "Adaptive controllers" group
```

No new CSS file — everything reuses `web/theme.css` tokens/classes (no edits needed; see reuse map). No changes to `mso-core.js`, `mso-sim.js`, `mso-registry.js`, `mso-priors.js`, `mso-optimize.js`, `mso-estimate.js`.

> Why a **separate** `online_parity_runner.js` rather than extending `parity_runner.js`: the existing runner imports the registry/priors/optimize modules (lines 11–14). Keeping the online runner free of those imports makes the anonymization guarantee structural — a grep for `registry` in the online path returns nothing. `test_parity.py` invokes both runners.

> **Pre-existing identity strings on edited pages are intentionally retained for the public OSS build, out of scope for the new artifacts.** Editing `index.html`/`cockpit.html` leaves their surrounding strings in place (`index.html` L11 author/title, L23 the GitHub URL + `pip install minimal-oversight`; `cockpit.html` footer `minimal-oversight==0.1.3`). The spec (L174–178) flags these and says a scrubbed variant is needed only for a blind-paper screenshot build. The **new** section and the new files carry **zero** author/venue/repo/arXiv strings; that is the only requirement here. If a blind-clean build is ever needed, add a documented scrub step for those three locations.

---

## (c) Component-reuse map

Every UI element maps to an existing class/idiom. Reused verbatim unless flagged NEW.

| Mock element | Reuses | Source (file:line) |
|---|---|---|
| Page chrome, `<h1>`/`.lede`/`.foot`, light/dark | `theme.css` body + tokens | `theme.css` 30–55 |
| **The one visible slider** (`.sl` row: label + range + value `<span>`) | `.sl` / `input[type=range]` | `theme.css` 44–47; idiom in `waterfilling.html` 13, `return-operator.html` 45–48 |
| "More controls" disclosure (collapses every other knob) | native `<details><summary>` styled with `.muted`/`.foot` | NEW micro-pattern (no JS); summary text = "Advanced: why exactly 2λ?" |
| Headline strip (plain-language outcome sentence above chart) | `.banner` + `--bg-success`/`--bg-danger` | `theme.css` 54, 12–14; live-recolor idiom in `cockpit.html` 805–815 |
| ONE big story-number card + small "details" row | `.grid` + `.card` (`.l`/`.v`); details row = a second `.grid` of smaller `.card`s or a `.muted` line | `theme.css` 40–43; idiom `return-operator.html` 38–43, `waterfilling.html` 16–21 |
| Direction-on-the-number ("1.0 = matches a perfect oracle · higher = worse") | `.card .l` caption + `.tag` | `theme.css` 41, 59 |
| Time-series chart (`<polyline>` cost lines, the duty sweep, the tracking streams) | `xFor(i)`/`yTop(v)` + `pts(arr,yf)` + `<polyline>` | `return-operator.html` 29–34, 59–62, 80–84 |
| Dashed analytic/optimum line (clairvoyant `1.0`, noise floor, `2−1/2λ` ghost, H_h asymptote) | `<line stroke-dasharray="4 4" stroke="#888780">` | `return-operator.html` 26–28, 70 |
| Two-fill bar + tick (held vs required budget; the fat-vs-thin margin bands) | `.bar` two-absolute-div fill idiom | `theme.css` 57; idiom `waterfilling.html` 60–63 |
| LRU/MARKER lane chips (h funded slots, k sink chips) | `.bar`/`.rx`/`.tag` row chips | `theme.css` 56, 59; `.rx` `cockpit.html`-style |
| Static \| Online toggle; LRU \| MARKER label | `.seg` segmented buttons + `.on` | `theme.css` 52–53; wiring idiom `waterfilling.html` 14, 65–68 |
| Play / Pause / Reset attract controls | plain `button` + `.on` | `theme.css` 48–51; idiom `return-operator.html` 14–17, 94–96 |
| **Node-graph (cockpit Online capstone):** nodes, edges, drag/pan/zoom | `el()`, `shapeEl()`, `render()`, `fit()`, `view`, `W/H/NS`, `CAT_SHAPE` | `cockpit.html` 489–490, 549–605 |
| **Moving bottleneck red dot** (walks `state.nodes` sinks under drift) | existing `lastBottleneck` red `circle{r:4,fill:"#E24B4A"}` | `cockpit.html` 594 |
| Per-sink review-budget bars breathing on nodes | extend node `<g>` with a `.bar`-style inline `rect` (teal held / amber tick) | NEW small addition inside `render()` node loop `cockpit.html` 579–601 |
| Token / step clock (requestAnimationFrame, dt-throttled, token objects) | `simLoop(ts)` + `simTokens` + `simRng=makeRng(7)` | `cockpit.html` 856, 867–873 |
| Deterministic seeded RNG (MARKER, attract jitter) | `mulberry32 makeRng` | `mso-sim.js` 25–33 |
| INFEASIBLE / unbounded stamp (text over chart, no rescale) | `.banner`-danger + SVG `<text fill="var(--red)">` | recolor idiom `cockpit.html` 813; red `#E24B4A` token |
| **Per-node inert drift field to promote (cockpit capstone)** | the field is keyed **`drift_rate`** on the live node object (the `nd()` factory assigns it from the template's `drift:` key); inspector slider + listener already exist | `cockpit.html` 198 (`nd()` assigns `drift_rate`), 652 (inspector field), 669 (listener); template `drift:` keys 144–193 |
| Masking A/B governance numbers — **OUT OF SCOPE for this showcase** (see note) | n/a | n/a |

**Color semantics (locked, theme tokens — `theme.css` 11):** `teal #1D9E75`=feasible/held-correctly/hit/funded; `amber #EF9F27`=margin/holding-overhead; `red #E24B4A`=refund/miss/infeasible/breach; `blue #378ADD`=online estimate; `dashed-grey #888780`=offline optimum/analytic floor.

> **Masking A/B surface — OUT OF SCOPE for this showcase.** The spec names Agent A (`p=0.186, M*=2.7`) / Agent B (`p=0.228, M*=8.1`), but none of the three layers actually mocks or flowcharts it; it appeared only as an "if surfaced" hedge. Asserting an anonymization guarantee against a surface that does not ship is confusing, and a builder cannot tell whether it ships or where. **Decision: it does not ship in this showcase.** The hedge is dropped. The anonymization guardrails that DO apply here are the concrete ones: `adaptive-online.js` must not import `mso-registry.js`/`mso-priors.js`, and the new artifacts carry no vendor names. (If Agent A/B is ever added later, it must be its own one-slider widget computing the numbers live via `mso-core.maskingIndex`/`sigmaCorrFixedPoint`, kept as bare "Agent A"/"Agent B" — feasible, since `masking.html` already computes these live, and the registry-leak risk is real because `cockpit.html`'s connector library carries real vendor names like HubSpot/Salesforce/Stripe/Auth0.)

### NEW chart types (no existing idiom — flagged)

1. **Diverging two-line "fork" with off-frame overflow** (hero). The `<polyline>` idiom exists, but **clamping a line to the frame top and stamping "unbounded" instead of auto-rescaling is new behavior** (Law 7). Build: compute `yFor(cost)` against a **fixed** domain `[0, optCost*3]`; any point above maps to `y=topPad` and sets an `overflow=true` flag → render the red `<polyline>` clipped at the top edge + a `<text>` stamp "pays 14.9× and rising · unbounded". Never expand the domain to contain it. ~40 lines.
2. **Lane race with travelling spotlight** (caching). Two horizontal lanes of `h` slot-chips; a spotlight `<rect>` walks the moving bottleneck; HIT=teal pulse, MISS=red flash + slot-eviction slide. No existing lane/spotlight idiom — built from `el()`-style SVG + the step clock. The **ratchet wall** (a held-slot stack growing past a red "pool capacity h" line → INFEASIBLE) is a separate beat, same primitives. ~120 lines (the L-effort driver).
3. **Fat-vs-thin margin bands bottoming on a floor line** (tracking). Two SVG bands drawn under the stream — a **fat amber** deadband band (half-height = `deadbandMargin`) and a **thin teal** Kalman band (half-height = the live `sqrt(var)`-scaled matched margin) — with a horizontal dashed-grey "noise floor" line the teal band visibly bottoms out on as ν→0. New composite; `<rect>` + dashed `<line>`. ~50 lines.

Everything else is assembled from existing idioms.

---

## (d) Parity plan — how `tests/test_parity.py` extends

The contract is unchanged: both sides compute from the **same inputs at test time**, agree to `|Δ| < 1e-6` (`test_parity.py` 4–6, 34, `_close` 370–376). Node-skip guard already present (36–39) covers the online runner too.

**Harness.** Add a second subprocess call alongside the existing one (`_run_node`, 379–389). New helper `_run_online_node(cases)` invokes `node scripts/online_parity_runner.js <in> <out>`. `online_parity_runner.js` is the mirror of `parity_runner.js` (9–18, 103) but `require("../web/adaptive-online.js")` **only** — no registry/priors import. New test function `test_online_browser_port_matches_python_reference()`; keep it a separate test so a failure localizes to the online module.

**Python references — note where each comes from (this is the build dependency made concrete):**
- **Ski-rental:** the per-phase helpers import from the package (`minimal_oversight.skirental`). The **full-instance** forms (`opt_cost`, `dwell_cost`, `required`, and the ratchet cost) are **not** in the package; load `scripts/online_skirental.py` via `importlib.util.spec_from_file_location` inside `_python_expected()` (or add `scripts/__init__.py`). For `ratchetCost` there is **no `ratchet_cost()` symbol** — the reference is `cost(*run("ratchet", required(W,tau,ncyc), lam)[:2], lam)`, verified `= 6431` at the hero point.
- **Tracking/Caching:** import from the **package** (`minimal_oversight.tracking`, `minimal_oversight.caching`) — `kalman_steadystate_var`, `ratchet_demand`, `cyclic_adversary`, `competitive_ratio`, `SharedPoolController`, etc. all live there. Use the `scripts/online_*.py` files **only** as the source of the observation stream (tracking) and the convergence-harness pattern (caching), never as the symbol source — their names differ (`kalman_steadystate_P`, `ratchet_capacity`, `cyclic`, no default seed).

**Three fixtures:**

1. **`skirental`** — Inputs: `lam∈{1,5,10,20}`, plus `(W,tau,lam,ncyc,d)` tuples covering the hero point **`(1,320,10,20)`** and `test_closedform_check` (`online_skirental.py` L133–144).
   - JS: `skirentalDwell, skirentalRatio, optSlackCost, dwellSlackCost, worstCaseRatio, minimaxDwell, optCost, dwellCost, ratchetCost`.
   - Python expected: package `skirental.skirental_dwell/ratio`, `opt_slack_cost`, `dwell_slack_cost`, `worst_case_ratio`, `minimax_dwell`; and (via importlib) `online_skirental.opt_cost/dwell_cost` + the `run("ratchet",…)`-based cost for `ratchetCost`. Assert `|Δ|<1e-6` scalar-wise via `_close`. **This machine-checks the 14.9 / 1.95 the hero shows at `τ=320`.**
2. **`tracking`** — Inputs: `(nu,sigma)` grid from `online_tracking.py test_floor_scales` (L138–139) incl. the headline `(0.02,0.20)`; `zDelta=2.054`.
   - JS: `kalmanSteadystateVar, matchedMargin, noiseFloorPerStep, deadbandMargin`; **plus `KalmanTracker`** driven over a **fixed shared observation array** (generate it in Python from `simulate(nu,sigma)` with a fixed seed, pass the literal `obs[]` + `r[]` arrays as inputs so RNG never crosses the language boundary) → compare the per-step `feasibleBudget` trajectory.
   - Python expected: package `tracking.kalman_steadystate_var`, `matched_margin`, `noise_floor_per_step`, `deadband_margin`; and a package `KalmanTracker` fed the same `obs[]`. Closed-form `P*` is deterministic → exact. The trajectory is exact because both filters consume identical observations.
3. **`caching`** — Inputs: cyclic streams `cyclic_adversary(h,rounds)` for `h∈{2,3,4,6,8}` and `{4,8,16,32}`; ratchet streams; a `SharedPoolController` request log.
   - **Deterministic part (exact, integer-equal):** `lruMisses, beladyMisses, ratchetDemand, cyclicAdversary`, and `SharedPoolController(policy='lru')` miss-counts vs the package. Integer counts → assert equality.
   - **MARKER (randomized) — two checks, neither is byte-parity vs NumPy:**
     - (i) **Determinism/reproducibility check (NOT a correctness check):** assert that JS `markerMisses` is *deterministic* under a fixed seed — same seed → same count. (The old "JS browser == JS Node, trivially same code" framing is a tautology and proves nothing about correctness; state it honestly as a reproducibility check.) **Optionally strengthen with a golden vector:** assert JS `markerMisses` on a fixed short hand-checked stream produces a known miss count — an exact correctness check that does not depend on NumPy parity.
     - (ii) **Asymptotic anchor convergence (the real correctness gate for MARKER):** assert the **mean over seeds** of `markerMisses/beladyMisses` lands within a tolerance band of the H_h anchor as `rounds` grows — compare `competitiveRatio('marker',…)` averaged over `seed∈range(8)` (mirrors `online_caching.py test_c3`) against `H_h = Σ 1/i` with a **finite-sample tolerance** (`|CR_empirical − H_h| < 0.25` at `rounds=400`, tightening with rounds), **not** `1e-6`. (Verified the band holds: max |Δ| ≈ 0.18.) The UI's "lengthen stream" probe is the same convergence the test encodes.

**Finite-sample handling for the asymptotic caching anchors (explicit).** The published LRU/MARKER ratios are limits in `rounds`. The fixture therefore (a) asserts **deterministic** policies exactly, and (b) asserts the **randomized** policy's seed-averaged ratio **converges toward** the harmonic anchor within a rounds-dependent band — it compares the *trend*, never the limit at finite N. A helper `_converges(empirical, anchor, band)` is added next to `_close` (370). Document this in the runner header and the test docstring so a future editor doesn't "tighten" it to `1e-6` and make it flaky.

---

## (e) Per-widget render approach

All widgets: framework-free, single `<script src="../adaptive-online.js">` (hero/caching/tracking) — **no other module needed** except cockpit (which keeps its existing six). Page background transparent via theme; `viewBox` SVGs scale to width like `return-operator.html` 19.

**Shared step-clock.** Reuse the `simLoop(ts)` pattern (`cockpit.html` 867–873): `dt = min(50, ts - last)`, advance state, `render()`, `requestAnimationFrame`. A single `playing` boolean + token guard (`return-operator.html` 93). One rAF per widget; cancel by flipping `playing`.

**No-axis-rescale overflow stamp (Law 7).** Fixed y-domain set at reset from the *clairvoyant optimum* (`optCost`), e.g. `domainMax = optCost*3`. `yFor(c)` clamps: `c > domainMax → y = topPad, overflow=true`. On overflow, draw the line clipped at the top edge and a `<text x=… y=topPad+14 fill="var(--red)">unbounded · pays {ratio.toFixed(1)}× and rising</text>`. The frame never grows. (Hero: ratchet line, stamping **14.9** at the `τ=320` extreme; caching: held-slot stack past the red `h` line stamps `INFEASIBLE`; tracking: the floor is a wall.)

**Hero (Law: hook before knob; worst-case framing kept honest).** Headline strip reads, e.g., **"never pays more than 2× — a worst-case guarantee"** over the flat teal line and **"pays 15× more and climbing"** over the diverging ratchet; the story-number card prints the live ratio with the direction caption "1.0 = matches a perfect oracle · higher = worse". The `dwell@2λ` line's "never more than 2×" is a *correct worst-case statement* (leave it). The proven bound `skirentalRatio(λ)` is the dashed-grey ghost the live curve keeps bumping into.

**Caching (worst-case qualifier at first use).** Mechanism glosses name the competitive ratio as a **worst-case/adversarial** fact, not typical-case: *"review pool = how many things you can watch at once"*, *"drop-longest-ago (LRU) can miss ~h× as often as a cheater who knows the future — **this is the worst case**, a stream engineered to defeat the pool; on ordinary streams it is far better"*, *"clairvoyant = a cheater who already knows the future"*. The cyclic-adversary lane is itself adversarial, so a one-line gloss keeps it honest without clutter. The "see the theory" reveal plots H_h as the dashed asymptote (object 2 above) and the live empirical ticks as the anchors (object 1), labelling MARKER **O(log h) ~ H_h asymptotically (worst-case-competitive)**.

**Tracking (CUT-GATE) — re-engineered cold-open: band thickness, NOT breach-count.** The native "breach spray" story is mathematically wrong for the calibrated pair: `z=2.054=Φ⁻¹(0.98)` targets exactly 2% infeasibility for **both** policies by construction. Verified against `scripts/online_tracking.py simulate(0.02,0.20)`: Kalman breach rate **2.09%**, naive deadband breach rate **1.93%** — the deadband breaches the **same or slightly less**, not more, and in a ~120-step window that is ~2 flashes each (a speckle, not a wall). So the cold-open leads with what is **actually true and visible**:
- **Two margin bands side by side on the same stream:** a **fat amber** deadband band (`deadbandMargin(σ)=z·σ=0.411`) and a **thin teal** Kalman band (`matchedMargin` ≈ `z·sqrt(P*)=0.127`). Headline strip: **"same safety target, 3.2× more wasted holding"** with the direction caption. The 3.24× thickness ratio is the 5-second story.
- The horizontal `noiseFloorPerStep(nu,sigma)` **dashed-grey "noise floor" line** is drawn; as the **one slider (ν)** → 0 the thin teal band shrinks and **visibly bottoms out on the floor line** (it never reaches 0). The floor `.card` shows `noiseFloorPerStep` with a locked **"can't go lower"** `.tag` (mirrors the ratchet's INFEASIBLE wall).
- **Red breaches are kept only as secondary texture, with the claim corrected** ("both policies breach ~2% — that is the calibrated feasibility target"). **Do NOT claim the deadband breaches more.** Optionally, an Advanced toggle can drop the naive policy's margin **below** `z·σ` (deliberately under-margined) to make a genuine red spray appear while Kalman stays clean — but that is a *reveal*, not the cold-open.

> **Ship gate (run honestly against the revised framing):** if a 5-second look at **the fat amber vs thin teal bands + the floor wall** reads as *"the naive way wastes a pile of holding for the same safety, and there is a hard floor you can't beat"*, ship it (one visible slider = ν; floor card stamped "can't go lower"). **If even the band-thickness gap does not read in <5s → cut from the showcase and keep the math as a paper figure** (per spec L100–115). The widget is built last of the three for exactly this reason.

**Auto-play attract-loop timeline (index hero).** Oversized ski-rental card, zero interaction: a scripted `tau` ramp (duty `0.05 → 0.003`, i.e. `τ` up to **320**) over ~6 s using the step clock; freeze at the fork the instant `overflow` flips true; stamp "bounded vs unbounded"; hold ~2 s; fade in `now you try →` linking to `widgets/skirental.html`. Pure presentation over `adaptive-online.js`, no new math (spec L79–87, effort S). Loops every ~30 s.

**`prefers-reduced-motion` (all widgets + attract-loop).** At load, `const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches`. If true: skip all rAF animation; render the **final/critical frame statically** — hero shows the already-forked lines with the **14.9** stamp; caching shows end-state counts + the INFEASIBLE wall; tracking shows the fat-vs-thin bands and floor line in place; the index hero renders the frozen fork (no sweep) with `now you try →` already visible. Every widget stays fully legible and correct with motion off (the gesture is *replayable*, never *required* to get the point).

---

## (f) Build sequence — effort + acceptance gate

Build strictly in this order (mirrors spec L147–163; hero validated before anything downstream; capstone last). **Nothing ships unless its gate is green AND parity stays green** (Law: machine-checked browser==paper is the differentiator).

| # | Step | Effort | Acceptance gate |
|---|---|---|---|
| 1 | **`web/adaptive-online.js`** — port all skirental/tracking/caching fns + the two stateful classes; UMD wrapper (code only, **no author header**); runs under Node; **no registry/priors import** | **M** | `node -e "require('./web/adaptive-online.js')"` loads clean; `AdaptiveOnline.skirentalRatio(10)===1.95`; **`ratchetCost(1,320,10,20)/optCost(1,320,10,20) ≈ 14.92` (i.e. `|x−14.9|<0.05`) at the hero point `τ=320`** — do NOT assert ≈14.9 at `τ=332` (that is 15.48); `grep -L 'registry\|priors\|Azevedo' web/adaptive-online.js` confirms no leak. |
| 2 | **`scripts/online_parity_runner.js` + `tests/test_parity.py` fixtures** — 3 fixtures; ski-rental full-instance forms loaded via importlib from `scripts/online_skirental.py`; tracking/caching from the package; deterministic-exact + finite-sample caching convergence + MARKER golden vector | **M** | `pytest tests/test_parity.py` green: skirental (incl. `(1,320,10,20)`) / tracking at `1e-6`; LRU/Belady/ratchet/`SharedPoolController('lru')` integer-equal; MARKER deterministic under fixed seed + golden-vector exact + seed-avg converges to H_h within band. **This gate gates every widget below.** |
| 3 | **HERO `web/widgets/skirental.html`** — duty sweep, two `<polyline>` lines, ONE slider (`tau`/duty, extreme `τ=320`), advanced knobs in `<details>`, headline strip, one story-number card, off-frame "unbounded" stamp | **M** | The single killer gesture: dragging duty toward `≈0.003` (`τ→320`) **forks the two lines** — ratchet escapes the frame stamped **"unbounded · 14.9× and rising"**, `dwell@2λ` stays flat ≈1.95× hugging the dashed 1.0; live curve lands on the `skirentalRatio` anchor ticks; exactly one visible slider on load; "never more than 2×" framed as a worst-case guarantee; reduced-motion shows the forked end-state with the 14.9 stamp. Ships only when fork reads in <3 s **and** step-2 parity green. |
| 4 | **`web/widgets/caching.html`** — two-lane LRU-vs-MARKER spotlight race on `cyclicAdversary` same seed; HIT/MISS pulses; ratchet wall as its own beat; Belady a dashed number; CR-vs-h as a `<details>` "see the theory" reveal with H_h as the dashed asymptote; "lengthen stream" probe | **L** | Two lanes only by default; LRU visibly evicts the next-requested slot while MARKER dodges; held-slot stack crosses the red `h` line → `INFEASIBLE` when distinct sinks > h; empirical miss-ratio dots converge onto the **finite-sample** anchors (LRU `~h`, MARKER `{2.06,2.68,3.28,3.88}`), with H_h drawn separately as the asymptote in the reveal; competitive ratios glossed as **worst-case** at first use; one visible knob (`h`). Parity green. |
| 5 | **`web/widgets/tracking.html`** (CUT-GATE) — Kalman vs naive deadband on one stream; **fat amber vs thin teal margin bands as the cold-open**; drawn noise-floor line; locked floor card; red breaches as corrected secondary texture | **M** | **5-second test on the band-thickness story:** fat amber (`z·σ=0.411`) vs thin teal (`z·sqrt(P*)=0.127`) bands + the floor wall read as *"same safety, 3.2× wasted holding, hard floor"* at a glance; one visible slider = ν shrinks the teal band onto the floor line; floor card stamped "can't go lower"; **no claim that the deadband breaches more** (both ~2%, the calibrated target). **If even this does not read in <5s → cut from showcase, keep as paper figure**; do not ship a flat third widget. Parity green either way. |
| 6 | **`web/index.html` + `mkdocs.yml`** — "Online oversight controllers" section, oversized auto-playing ski-rental hero card, sequence-framing copy, three cards; nav group | **S** | Attract-loop sweeps to the fork (`τ→320`) with zero interaction, freezes, stamps "bounded vs unbounded · 14.9×", fades in `now you try →`; respects reduced-motion; cards link to the three widgets; mkdocs builds; **the new section carries no author/venue/repo/arXiv strings** (pre-existing page strings on `index.html` are intentionally retained for the public build). |
| 7 | **Capstone `web/widgets/cockpit.html`** — promote the inert per-node **`drift_rate`** field (assigned by `nd()` at L198 from each template's `drift:` key; inspector at L652, listener at L669) into a `Static | Online` `.seg` toggle; in Online mode the red bottleneck dot walks `state.nodes` sinks under drift, per-sink budget bars breathe (teal held / amber required tick), hold/release events fire, shared-pool occupancy animates vs `h`; readouts in existing `theory-readout` (L124)/`recipes` (L125); add 1–2 multi-sink templates | **L** | Toggle Online on a multi-sink template → bottleneck dot **moves** between sinks under drift (reuse `lastBottleneck` red dot L594); budget bars breathe; pool occupancy animates against `h`; reuses `analyzePipeline` `min`-over-sinks (don't re-derive); Static mode byte-identical to today; reduced-motion renders a static Online snapshot. Built last; only after widgets 3–5 validate the module. |

**Global gates (every step):** exactly ONE visible slider per widget on load; plain-language headline strip present; direction printed on every headline number; one big story-number card with intermediates demoted to a details row; jargon glossed at first use (competitive ratios qualified as **worst-case**); secondary "see the theory" chart is a `<details>` reveal, not the cold-open; failing lines run off-frame stamped unbounded/INFEASIBLE (never auto-rescaled); color semantics locked to the theme tokens; **the new artifacts carry no author/venue/repo/arXiv strings; `adaptive-online.js` does not import `mso-registry.js`/`mso-priors.js`; the masking A/B surface is out of scope.**

---

### Key file references for the implementer
- UMD **code** wrapper to mirror (not the author header): `web/mso-core.js:16-19`; parity contract: `tests/test_parity.py:370-389`, `scripts/parity_runner.js:9-18,103`
- Math source of truth: package per-phase forms `src/minimal_oversight/{skirental,tracking,caching}.py`; **hero full-instance forms** `scripts/online_skirental.py:45,108,115` + ratchet via `run("ratchet",…)`+`cost(...)` `:81-103,127`; tracking instance `scripts/online_tracking.py:51-77`; caching convergence harness `scripts/online_caching.py:166-179`
- Idioms: time-series `web/widgets/return-operator.html:29-34,59-62,80-84,93`; two-fill bar `web/widgets/waterfilling.html:60-63`; `.seg` toggle wiring `:14,65-68`; node-graph engine `web/widgets/cockpit.html:489-490,549-605`, step clock `:856,867-873`, inert `drift_rate` (assigned by `nd()`) `:198`, inspector field/listener `:652,669`, template `drift:` keys `:144-193`, moving-bottleneck red dot `:594`, `theory-readout`/`recipes` panels `:124-125`; mulberry32 `web/mso-sim.js:25-33`; design tokens/classes `web/theme.css:11,40-59`
- Anonymization guardrails: `COCKPIT_ONLINE_SHOWCASE.md:165-178` — `adaptive-online.js` must not import registry/priors; the new section + new files carry zero author/venue/repo strings; masking A/B out of scope.
