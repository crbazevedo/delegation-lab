# Docs to slot in for the online module (uncommitted)

The adaptive controller + variants ship as code on `feat/adaptive-review-variants`, and the page
`docs/methodology/online-control.md` is written. Three small edits remain in files that are
currently modified by other work, so they are left here for you to slot in by hand (none contains
paper text).

## 1. README — add to the features list

```markdown
### Online review control under drift

Re-allocate review at runtime as competence drifts, with competitive guarantees:

- **Ski-rental release** (`minimal_oversight.skirental`) — release-vs-hold is rent-or-buy; the
  `2·lambda` dwell is `2 − 1/(2·lambda)`-competitive.
- **Noise-robust tracking** (`minimal_oversight.tracking`) — a Kalman estimator + matched margin;
  the holding overhead has an irreducible `sqrt(nu·sigma)` floor.
- **Shared-pool scheduling** (`minimal_oversight.caching`) — a finite shared review pool behaves as
  online paging: LRU is `Theta(h)`-competitive, MARKER `O(log h)`.

See _Methodology → Online review control_.
```

## 2. CHANGELOG.md — add under `[Unreleased]`

```markdown
### Added
- `minimal_oversight.online_control`: runtime review controller (marginal ratchet + hysteresis
  release) with machine-checked invariants (Z3 + TLA+).
- `minimal_oversight.skirental`, `.tracking`, `.caching`: the release / noise-tracking /
  shared-pool variants as importable, unit-tested modules.
- Methodology docs: _Online review control_.
```

## 3. mkdocs.yml — add to the `Methodology` nav section

```yaml
  - Online review control: methodology/online-control.md
```
