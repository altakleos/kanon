---
status: accepted (lite)
date: 2026-05-01
weight: lite
---
# ADR-0038: `kanon init` merges into an existing `AGENTS.md` instead of skipping or overwriting

## Decision

`kanon init` no longer treats a pre-existing `AGENTS.md` as untouchable. Three branches by precedence:

1. **Absent** — write the full kit-rendered `AGENTS.md` (today's behavior).
2. **Existing, has at least one `<!-- kanon:begin:<section> -->` marker** — refresh marker bodies, preserve outside content byte-for-byte. Same primitive `kanon upgrade` already uses (`_merge_agents_md`). `init` and `upgrade` converge on this branch.
3. **Existing, no kanon markers** — *prepend* the full kit-rendered `AGENTS.md` above the existing prose, separating the two with a `## Project context` H2. Existing prose is preserved verbatim under the H2.

`--force` is not required for any branch; init never destroys existing user-authored prose. Spec amendment: `cli.md` INV-cli-init-agents-md-merge.

## Why

Pre-v0.3.0a8 behavior: `init` ran `_assemble_agents_md()` and wrote the result via `_write_tree_atomically`, which silently skipped pre-existing files. Lived UX (smoke-tested against an existing project): `kanon init . --profile max` succeeded, scaffolded `.kanon/`, `docs/`, `ci/`, `.github/`, `scripts/`, and reported `✓ Created kanon project` — but **`AGENTS.md` was never written**. The existing 23-line stub remained as the canonical agent boot doc, with zero references to the depth-3 hard gates, protocols-index, or contribution conventions the kit just scaffolded. The kit's whole value proposition ("agent reads AGENTS.md and follows the process", per ADR-0003) silently fails in this scenario.

The merge primitive already exists. `_scaffold._merge_agents_md(existing, new_agents)` is what `kanon upgrade` uses to fold kit-managed marker sections into existing prose. There is no principled reason `init` and `upgrade` should diverge on AGENTS.md — both are scaffold operations, both should converge on the same merge contract.

The "no markers" branch is the design call. Two viable placements for the existing prose:

- **(A — chosen)** *Prepend kit content above existing prose.* The hard-gates table and protocols-index sit at the top of the file; existing prose moves to a `## Project context` H2 below. Aligns with [ADR-0010](0010-protocol-layer.md) / [ADR-0034](0034-routing-index-agents-md.md) enforcement-proximity principle: gates need to be load-bearing on first read, before the agent forms a mental model from the project-author's framing.
- **(B — rejected)** *Append kit content below existing prose.* Preserves "this is my project" framing first. Weakens enforcement proximity for the hard gates because they no longer appear at the top of the canonical boot doc.

(A) wins on the kit's own enforcement-proximity grounds; the "## Project context" H2 makes it explicit that the existing prose has been preserved, not subordinated.

## Alternative

Refuse `init` when `AGENTS.md` exists without `--force`. Rejected — friction theater. Most users with an existing AGENTS.md will delete it and re-run, losing prose; the kit teaches them it destroys content. Merge teaches them the kit collaborates.

## References

- [`docs/specs/cli.md`](../specs/cli.md) — INV-cli-init-agents-md-merge.
- [`docs/plans/init-agents-md-merge.md`](../plans/init-agents-md-merge.md) — implementing plan.
- [ADR-0003](0003-agents-md-canonical-root.md) — `AGENTS.md` is the canonical agent boot doc.
- [ADR-0010](0010-protocol-layer.md), [ADR-0034](0034-routing-index-agents-md.md) — enforcement-proximity principle.
