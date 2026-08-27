# Minimal Oversight - AGI Club Sao Paulo 2026

Canonical, self-contained publication of the PT-BR talk delivered at AGI Club
Sao Paulo in 2026.

## Published artifacts

- `index.html` - interactive 16:9 presentation; no build step or external assets
- `minimal-oversight-agi-club-sp-2026.pdf` - printable 52-slide export

Live URLs:

- Presentation: <https://crbazevedo.github.io/delegation-lab/talks/agi-club-sp-2026/>
- PDF: <https://crbazevedo.github.io/delegation-lab/talks/agi-club-sp-2026/minimal-oversight-agi-club-sp-2026.pdf>

## Controls

- `Left` / `Right`, `Page Up` / `Page Down`, or `Space`: navigate
- `G`: open the slide index
- `N`: toggle presenter notes
- `Home` / `End`: first / last slide

## Provenance and publishing

The source was authored in Slide Agent Studio and exported as a standalone HTML
file. The publishing copy removes editor-only DOM, rebuilds the table of contents
at runtime, and excludes slides marked `data-hidden="true"`. The authored Studio
file remains untouched.

`.github/workflows/docs.yml` stages `talks/` into the MkDocs build. A push to
`main` therefore publishes both artifacts through the repository's existing
GitHub Pages site.
