# Project documentation — Meeting Assistant

## Index

Three main documents in **English** (LTR) — each has a matching PDF in `pdf/`:

| File | Content |
|------|---------|
| [01-project-overview.html](01-project-overview.html) | **Project overview & vision** |
| [02-implementation.html](02-implementation.html) | **Technical implementation** |
| [03-roadmap-and-future-work.html](03-roadmap-and-future-work.html) | **Roadmap & future work** |

Additional resources:

| File | Content |
|------|---------|
| [CHANGELOG.md](CHANGELOG.md) | **Change history** — update with each feature |
| [screenshots/](screenshots/) | **UI/UX screenshots** — home, meeting, tasks, settings |
| [superpowers/specs/2026-05-26-meeting-assistant-design.md](superpowers/specs/2026-05-26-meeting-assistant-design.md) | Design spec |
| [superpowers/specs/future-sprints-roadmap.md](superpowers/specs/future-sprints-roadmap.md) | Sprint roadmap (Markdown) |

## View HTML

Open `.html` files in a browser (LTR, Mermaid diagrams).

## PDF and SVG (automated export)

```bash
chmod +x scripts/export-docs.sh
./scripts/export-docs.sh
```

| Output | Path |
|--------|------|
| **PDF** (English LTR) | [docs/pdf/](pdf/) |
| **SVG** (Mermaid diagrams) | [docs/diagrams/](diagrams/) |
| **UI screenshots** (Playwright) | [docs/screenshots/](screenshots/) |

To refresh UI screenshots (backend + frontend must be running):

```bash
chmod +x scripts/capture-ui-screenshots.sh
./scripts/capture-ui-screenshots.sh
```

Requirements: Node.js 20+, internet (first run for npm and fonts).
