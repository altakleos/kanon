---
status: accepted
date: 2026-04-24
---
# ADR-0018: Invariant IDs — stable anchors for spec invariants

## Context

Specs reference invariants by ordinal ("invariant 3"). Inserting a new invariant silently shifts all downstream references. ~125 invariants across ~16 spec files, ~17 ordinal references in plans/ADRs.

## Decision

1. Each invariant gets an HTML comment anchor: `<!-- INV-<spec-slug>-<short-name> -->` on the line before it.
2. `<spec-slug>` = filename stem. `<short-name>` = kebab-case `[a-z][a-z0-9-]{1,40}`, derived from the invariant's bold name.
3. Anchors are append-only (never reused after deletion).
4. A CI validator checks anchor uniqueness, slug consistency, and cross-reference resolution.
5. `kanon verify` warns on missing anchors at SDD depth ≥ 2.
6. Big-bang migration: all accepted specs retrofitted in one pass.

## Alternatives Considered

**Markdown heading IDs.** Rejected — pollutes document outline, breaks numbered-list structure.
**Incremental migration.** Rejected — creates mixed state, makes validator harder to write.

## Consequences

- All accepted specs gain `<!-- INV-* -->` anchors.
- Plans/ADRs update ordinal references to INV-* slugs.
- Spec template updated with anchor convention.
- New CI validator (or check_foundations.py extension).

## References

- [Spec: Invariant IDs](../specs/invariant-ids.md)
- [Spec: Verified-By](../specs/verified-by.md) — companion (deferred)
