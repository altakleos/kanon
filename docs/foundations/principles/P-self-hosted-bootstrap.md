---
id: P-self-hosted-bootstrap
kind: technical
status: accepted
date: 2026-04-22
---
# The kit uses itself to develop itself

## Statement

`kanon` is developed using `kanon`. The repo is a tier-3 `kanon` project. Its own `docs/` tree and the tier-3 template it ships share source of truth (byte-identical where files are shared), enforced by CI. A kit that can't be used to develop itself is by definition not ready to ship.

## Rationale

Self-hosting is the cheapest test of fitness. If the kit's AGENTS.md and process gates feel onerous when applied to the kit's own evolution, they will feel worse when adopted by external projects. If the kit's tier-3 template drifts from the kit's own shape, consumers will adopt the template and produce projects that don't look like the reference. Both failure modes are obvious only when self-hosting is mandatory.

## Implications

- The kit's AGENTS.md is simultaneously the kit's own contributor boot document and the tier-3 template's AGENTS.md (modulo project-specific placeholders). `ci/check_kit_consistency.py` enforces byte-equality on shared sections.
- The kit's `docs/development-process.md` is the exact file scaffolded into tier-1 through tier-3 consumer projects. A change to this file in the kit's repo must pass the same validators consumers will run.
- When the kit ships a new capability (e.g., a future spec-graph-tooling release), the kit itself must adopt it before the release is cut. "We built it but we don't use it" is a red flag.
- The self-hosting paradox (the kit requires itself to develop itself, but commit 1 can't follow a method that doesn't yet exist) is resolved by ADR-0002's three-commit bootstrap.

## Exceptions / Tensions

- Some kit-specific files (the CLI source, the pip metadata, the templates directory) have no analogue in the tier-3 template. Those are producer-only concerns; they don't participate in the byte-equality check.
- Major kit refactors may temporarily break self-hosting between commits. Those commits should be bounded and named, analogous to the bootstrap phase.

## Source

User requirement during v0.1 planning ("the kanon should be developed using kanon!"). Formalised as a principle because it shapes many downstream decisions (the check_kit_consistency validator, the tier-3-is-the-repo design, the three-commit bootstrap ADR).
