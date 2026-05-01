---
id: P-cross-link-dont-duplicate
kind: technical
tier: kit-author-internal
status: accepted
date: 2026-04-22
---
# Cross-link artifacts; never duplicate content

## Statement

When two documents or files might share content, they are either byte-identical (one canonical source enforced by CI) or they link to each other. Duplication — where the same content is copy-pasted with no mechanical tie — is a process smell and eventually a correctness bug.

## Rationale

Duplication looks cheap at authoring time and becomes expensive the first time an edit lands in one copy and not the other. Agents and humans alike hit the stale copy, follow it, and produce incoherent work. The cost is paid not at write time but at every subsequent read.

This is why the kit's shims (per ADR-0003) are pointers, not content copies. Why the kit's tier-3 template uses the kit's own canonical docs (enforced by `check_kit_consistency.py`). Why `AGENTS.md` and `docs/sdd-method.md` share the byte-identical trivial/non-trivial bullet lists (verified with `diff`).

## Implications

- When the same rule must appear in two artifacts for reader convenience, it is authored once in the canonical location and either (a) included verbatim with a validator enforcing byte-equality, or (b) replaced with a one-line pointer.
- The `ci/check_links.py` validator guards against broken cross-references. The `ci/check_kit_consistency.py` validator guards against shared-file drift.
- When tempted to copy-paste a paragraph from one file to another, default to a link. If the content truly must appear inline (e.g., an agent's context window won't follow the link reliably), document the duplication and enforce it mechanically.

## Exceptions / Tensions

- Some duplication is necessary for reliability with LLM agents whose context budgets don't always resolve links. The v0.1 kit accepts a small amount (trivial/non-trivial bullets in AGENTS.md ↔ sdd-method.md) and enforces it via CI.
- Historical records (ADRs, plans) are intentionally static and do not back-reference later decisions that supersede them — supersession flows forward only, which is not strictly duplication but a related pattern.

## Source

Sensei's foundational convention (`cross-link-dont-duplicate`) ported unchanged. Observed pain during Sensei's own development: cross-reference drift between AGENTS.md and sdd-method.md was the motivating failure mode.

## Tier

This principle is **kit-author-internal** (per [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md)). It governs kit-author hygiene during prose authoring; it is not part of the substrate's published protocol. Publishers do not need to honour it; the substrate does not enforce it on consumer repos. Body amendments are kit-author concerns and do not require dialect supersession.
