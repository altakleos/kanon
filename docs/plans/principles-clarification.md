---
feature: principles-clarification
status: done
date: 2026-04-27
---
# Plan: Clarify the kit-shipped principles README that kit principles don't propagate

## Context

The Round-2 verification panel and the maintainer's subsequent "principles authoritative until overridden by downstream consumer" answer were both grounded in an implicit assumption that the kit's own `docs/foundations/principles/P-*.md` files propagate to consumers via `kanon init` / `kanon upgrade`. **They do not.**

What the `kanon-sdd` aspect actually scaffolds at depth 3 (per `src/kanon/kit/aspects/kanon-sdd/manifest.yaml`):

```yaml
depth-3:
  files:
    - docs/foundations/principles/README.md   # ← only the index/template prose
    - docs/foundations/personas/README.md     # ← only the index/template prose
    - docs/foundations/vision.md              # ← stub vision template
    - docs/foundations/README.md
    - docs/design/README.md
    - docs/design/_template.md
```

Notably absent: any `P-*.md` files. The kit's own `docs/foundations/principles/P-prose-is-code.md`, `P-tiers-insulate.md`, `P-self-hosted-bootstrap.md`, `P-specs-are-source.md`, `P-cross-link-dont-duplicate.md`, and `P-verification-co-authored.md` are kit-author internal stances. They are never copied into a consumer's tree.

This plan supersedes Track 3 of `docs/plans/fidelity-and-immutability.md`. The originally-specced principle-override mechanism (consumer overrides kanon's kit principles) was solving a non-problem: there is nothing to override, because consumers never receive kit principles in the first place.

The actual gap is documentation: the scaffolded `docs/foundations/principles/README.md` should make the kit-vs-consumer separation explicit so future readers (consumer agents and human contributors alike) don't repeat the misframing.

## Tasks

- [x] T1: Add a clarifying paragraph to the **kit-shipped** principles README (consumer-facing) explicitly stating that the directory belongs to the consumer and that kanon's own kit-author principles are not present → `src/kanon/kit/aspects/kanon-sdd/files/docs/foundations/principles/README.md`
- [x] T2: Add a parallel one-line note to kanon's own **repo** principles README pointing at the kit-shipped starter README and clarifying that consumers do not receive the kit's principle files. The two READMEs are NOT byte-locked (confirmed: `kanon-sdd/manifest.yaml`'s `byte-equality:` block does not list them); this is a parallel edit, not a mirror. → `docs/foundations/principles/README.md` (depends: T1)
- [x] T3: Refresh `.kanon/fidelity.lock` (the README SHA changes) → `.kanon/fidelity.lock` (depends: T1, T2)
- [x] T4: Append CHANGELOG entry under `[Unreleased]` § Changed → `CHANGELOG.md` (depends: T1)
- [x] T5: Mark Track 3 of `docs/plans/fidelity-and-immutability.md` as deferred-with-rationale, citing this plan as the closure → `docs/plans/fidelity-and-immutability.md`
- [x] T6: Set this plan's status to `done` once T1–T5 are committed and verify is clean → `docs/plans/principles-clarification.md`

## Acceptance Criteria

- [x] AC1: The scaffolded `docs/foundations/principles/README.md` explicitly states (in prose, not just by inference) that kit-author principles are kit-internal stances and do not propagate to consumer projects.
- [x] AC2: Kit + repo copies of the principles README each carry the appropriate clarifying prose (kit-shipped: consumer-facing "this directory is yours"; repo: kit-author-facing "consumers don't receive these files"). They are NOT byte-identical and are not required to be — the kit-shipped one is a starter template; the repo copy is kanon's own catalog.
- [x] AC3: `kanon verify .` returns `status: ok` with zero warnings.
- [x] AC4: `python scripts/check_kit_consistency.py` returns `status: ok`.
- [x] AC5: `pytest`, `ruff`, `mypy` clean.
- [x] AC6: Track 3 of `fidelity-and-immutability.md` reflects the new framing (deferred-and-explained, not silently abandoned).

## Documentation Impact

- `docs/foundations/principles/README.md` (kit + repo) — one clarifying paragraph.
- `CHANGELOG.md` — `[Unreleased]` § Changed entry naming the clarification.
- `docs/plans/fidelity-and-immutability.md` — Track 3 status reflects the deferral with citation back to this plan.

## Out of Scope

- The originally-specced Track 3 "Option (b) principle-override frontmatter + spec + ADR + validator extension" — explicitly **not** shipping. The mechanism solves a problem consumers don't have.
- Any kanon-internal CI gate enforcing immutability of kit-author principles (analogous to ADR-0032's gate over `docs/decisions/`). Could be useful at scale but not addressed here.
- Re-evaluating the Round-2 framing in retrospective narrative form — that's a maintainer-facing reflection, not a kit-shipped artifact.
