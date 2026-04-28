---
status: done
design: "Prose-only changes to existing docs"
---

# Plan: Reduce agent context overhead (Track C)

## Problem

At max depth, the boot chain consumes ~12,250 words before any work begins.
A single code change triggers 6 protocols (~3,000 more words). The ADR index
lists 33 entries with no triage guidance. Agents under context pressure will
skim, skip, or hallucinate compliance.

## Changes

### C1. Add task-type triage to the boot chain

Add a "Quick Start by Task Type" section to AGENTS.md (after the boot chain)
that tells agents which docs to read based on what they're doing:

| Task type | Must read | Can skip |
|-----------|-----------|----------|
| Bug fix (single file) | AGENTS.md gates only | vision, dev-process, foundations |
| Feature (new capability) | Full boot chain | — |
| Refactor (no behavior change) | AGENTS.md gates, kanon-implementation | vision, specs, foundations |
| Docs/prose only | AGENTS.md contribution conventions | everything else |
| CI/tooling | AGENTS.md gates, kanon-implementation | vision, dev-process |

This doesn't remove any content — it gives agents permission to skip
irrelevant material, reducing effective context load by 40-60% for most tasks.

### C2. Add category tags to ADR index

Add category tags to `docs/decisions/README.md` entries so agents can filter
by relevance. Categories: `cli`, `process`, `kit-internals`, `aspects`,
`testing`, `release`. An agent working on CLI code reads `cli` + `aspects`
ADRs; an agent writing tests reads `testing` ADRs.

### C3. Add "skip when N/A" guidance to completion checklist

The completion checklist protocol fires on every task completion with 9 items.
Add a preamble that says: for changes that don't touch dependencies, security,
or docs, items 4-6 are automatically N/A — state "N/A: no deps/security/docs
changes" in one line rather than justifying each individually.

## Acceptance criteria

- [x] AGENTS.md has a task-type triage table after the boot chain
- [x] decisions/README.md entries have category tags
- [x] Completion checklist has streamlined N/A guidance
- [x] Kit bundle counterparts updated (check_kit_consistency passes)
- [x] No behavioral changes — all prose only
