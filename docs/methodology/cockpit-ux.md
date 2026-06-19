# Cockpit design rationale

The [cockpit](https://crbazevedo.github.io/delegation-lab/app/widgets/cockpit.html)
is meant to make governance theory *usable* on real agentic workflows. Its UX
follows four evidence-backed pillars from a 2026 design-research sweep; each
maps to a concrete choice in the tool.

## 1. The graph editor

Node-link diagrams are read by their **node encoding** first
([Munzner, *Visualization Analysis & Design*](https://www.cs.ubc.ca/~tmm/vadbook/)).
So each node is a compact card with a fixed hierarchy — **label → model · cost →
component type · masking** — truncated to width so it never overflows or collides
with an edge. Workflows are placed by a **layered (Sugiyama-style) auto-layout**
([Eclipse ELK](https://eclipse.dev/elk/blog/posts/2025/25-08-21-layered.html))
so larger cards never overlap. Edges stay simple curves: the strong claims that
one edge style universally wins did *not* survive verification, so we don't
over-engineer routing.

## 2. The analytics panel

"Overview first, then details on demand." The panel **leads with the verdict**
(FEASIBLE / AT-RISK / INFEASIBLE) and the four headline numbers, and pushes
provenance and per-node internals behind **progressive disclosure** — because
*over*-transparency can *reduce* trust
([Eiband et al., 2021](https://arxiv.org/abs/2108.13270);
[Google PAIR, Explainability + Trust](https://pair.withgoogle.com/chapter/explainability-trust/)).
Priors carry confidence and bands (a *calibrated* signal, not a maximised one);
they're surfaced where you act on them (the seed modal, the inspector), not
stamped on every card.

## 3. The optimizer result

A live, explained result is trusted far more than a bare diagram
([Drozdal et al., AutoML trust, IUI 2020](https://arxiv.org/pdf/2001.06509)).
Two design rules follow:

- **Lead with the outcome, demote the internals.** Each allocation card shows
  C_op, $/run, "Nx cheaper" and the open-source share up front; the move-by-move
  step list is collapsed under "what changed".
- **Surface a set; let the human choose a-posteriori — never auto-commit.**
  Following [PAVED (Cibulski et al., EuroVis 2020)](https://onlinelibrary.wiley.com/doi/10.1111/cgf.13990),
  "⚡ Optimize" *previews* a small cost↔quality frontier ("Min cost · meets
  target", "More headroom", "Fit budget") and applies nothing until you click
  **Apply** on the one you want. PAVED's store/raw-values/export guidance also
  motivates the **Export** button (download the pipeline + its governance numbers
  as JSON).

## 4. Time-to-first-value

Expert tools win on a fast first success, so the cockpit opens on a realistic,
model-loaded template (not a blank canvas), every template carries a one-line
description with a "what to try" nudge, and the menu is grouped by industry.

---

**Caveat.** These are design *priors* too: the AutoML/PAVED findings are
extrapolated from adjacent domains (AutoML, engineering-design trade-offs), and
the agentic-workflow tooling space is young. The cockpit should keep evolving
with real usage. Full provenance for the sweep lives alongside the
[priors evidence ledger](priors-evidence.md).
