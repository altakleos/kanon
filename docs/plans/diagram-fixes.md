---
status: done
slug: diagram-fixes
date: 2026-05-01
design: "Bug fix to the contributor doc shipped in PR #48; no design surface."
---

# Plan: Redesign mermaid diagrams as conceptual pictures

## Goal

The 6 mermaid diagrams in `docs/contributing.md` (PR #48) are too low-level — each one names modules, files, and function calls, duplicating the tables below it. They should carry the *shape* of the idea so a new contributor's mental model snaps into place. Implementation detail belongs in the tables and prose right below each diagram, not in the diagram itself.

## Redesign

| # | Current (low-level) | Redesigned (conceptual) |
|---|---|---|
| 1 Mental model | 8 nodes, module names, crossing edges | 3 actors (KIT / CONSUMER REPO / AGENT) and 4 verbs on the edges |
| 2 Aspect model | 13 nodes including all 7 aspect names + provides strings | What an aspect *is*: one box opens to its 4 ingredients sitting on a depth dial; per-aspect enumeration stays in the table |
| 3 Running kanon | 6 swim lanes, 12+ function-level messages | 3 actors (USER / kanon / REPO), three verbs (plan, transform atomically, verify) |
| 4 Source layout | 13 file-named nodes, hairball edges | 4 layer-boxes (Dispatcher / Domain logic / I/O kernel / Validators); file names live only in the table below |
| 5 CI workflow | 8 nodes naming workflow files + jobs | Concentric gates (onion): universal → structural → semantic |
| 6 Verify pipeline | 5-participant sequence with ADR footnote | **Drop entirely.** Replaced by one sentence in §6 prose; the conceptual story is already in diagram 3 |

## Scope

### In scope

- Edit `docs/contributing.md` only.
- Replace the 6 mermaid blocks with the 5 conceptual blocks above.
- Adjust the 1–2 sentences of prose surrounding each diagram if needed to read with the redesigned picture.

### Out of scope

- Source / spec / ADR / design-doc change.
- Other markdown files.
- Adding tests or CI checks for mermaid rendering.
- Restructuring section order, adding new sections, or rewriting non-diagram prose.

## Acceptance criteria

- [x] Diagram count drops from 6 to 5.
- [x] No mermaid node label names a Python module, file path, function call, or ADR number.
- [x] All diagrams use `flowchart` (not `graph`) directives where applicable.
- [x] No `<br/>` inside any `sequenceDiagram` `Note over` line.
- [x] No HTML entities (`&lt;`, `&gt;`) inside any quoted node label; use literal `<`/`>`.
- [x] No Unicode arrows inside Notes (use ASCII `->`).
- [x] Every section that had a diagram still has a clear conceptual diagram, and the surrounding prose still reads cleanly.
- [x] Doc length stays ≤ 400 lines (was 365).
- [x] `kanon verify .` returns `status: ok`.
- [x] `python scripts/check_links.py` passes.
- [x] No CHANGELOG entry needed (docs-only).

## Verification

GitHub mermaid rendering can only be confirmed by viewing on github.com after push. After PR is open, inspect rendered diagrams in the PR's "Files changed" view; if any diagram still looks crowded, iterate.

## Documentation impact

- Touched: `docs/contributing.md` (mermaid blocks + immediate-prose tweaks only).
- No spec / design / ADR change.
