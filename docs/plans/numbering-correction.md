---
status: draft
slug: numbering-correction
date: 2026-05-01
design: "No design surface. Mechanical correction of an ADR-numbering placeholder ('0040.5') that violated the integer-only convention before any Phase 0 ADRs cite it."
---

# Plan: Numbering correction — flush "0040.5" before Phase 0 ADRs land

## Context

During panel-review rounds 3–5, an ADR-numbering placeholder `0040.5` was used to flag the kernel/reference runtime interface ADR as architecturally adjacent to ADR-0040 (realization-shape + grammar). The placeholder leaked into shipped artifacts (ADR-0048 body, CHANGELOG, the foundations-rewrite plan, the specs-designs-cleanup plan).

ADR numbering in this project is integer-only by convention (`docs/decisions/0001-...` through `docs/decisions/0048-...`; no decimals). Catching this before any Phase 0 ADR cites `0040.5` lets us ship Phase 0 with clean integer numbering throughout.

## Renumbering decision

The kernel/reference runtime interface ADR — the panel's "0040.5" — takes integer slot **0040**, preserving its architectural adjacency to the realization-shape + grammar ADR (which moves to 0041). All subsequent Phase 0 ADRs shift down by one:

| Panel placeholder | Correct ADR | What it ratifies |
|---|---|---|
| ADR-0039 | **0039** | Contract-resolution model |
| ADR-0040.5 | **0040** | Kernel/reference runtime interface |
| ADR-0040 | **0041** | Realization-shape + grammar |
| ADR-0041 | **0042** | Verification scope-of-exit-zero |
| ADR-0042 | **0043** | Distribution-boundary + cadence |
| ADR-0043 | **0044** | Substrate self-conformance |
| ADR-0044 | **0045** | De-opinionation transition |

Phase 0 spans ADRs 0039–0045.

## Scope

### In scope

#### A. ADR-0048 body edit (immutability-trailer required)

`docs/decisions/0048-kanon-as-protocol-substrate.md` line 55: replace the parenthetical `(0039–0044, plus 0040.5 kernel/reference runtime interface)` with `(0039–0045)`. This is a body edit on an `accepted` ADR, requiring the `Allow-ADR-edit:` commit trailer per ADR-0032's exception class #3 ("explicit opt-out via a commit-message trailer").

The trailer text:

```
Allow-ADR-edit: 0048 — fix planning-placeholder ADR-numbering reference '0040.5' to integer-only '0040..0045' range; numbering placeholder leaked from panel review and violates integer-only convention.
```

This is the textbook trailer use-case (factual correction; no semantic change to the decision).

#### B. Free edits (no immutability gate)

- **`CHANGELOG.md`** (line 11): the `[Unreleased]` paragraph references `Phase 0 ADRs (0039–0044, plus 0040.5 kernel/reference runtime interface)`. Replace with `Phase 0 ADRs (0039–0045)`.
- **`docs/plans/foundations-rewrite.md`** (3 references at lines 19, 108, 114): replace `0040.5` references with the correct integer slot per the renumbering table.
- **`docs/plans/specs-designs-cleanup.md`** (line 52): the out-of-scope list cites Phase 0 ADRs as "(0039–0044, 0040.5)". Replace with `(0039–0045)`.

### Out of scope

- **Phase 0 ADRs themselves.** None exist yet; numbering is established by this PR for them to use.
- **ADR-0048 semantic content.** The decision is unchanged; only the numbering reference is corrected.
- **No source / spec / aspect-manifest / protocol-prose / design-doc / foundations changes.** Pure documentation correction.
- **No new principle, persona, or invariant.**
- **No CHANGELOG entry under `[Unreleased]`.** This is a correction to an existing entry, not a new user-visible change.

## Approach

1. **Edit ADR-0048** (line 55 — single-line body edit).
2. **Edit CHANGELOG.md** (line 11 — single-paragraph correction).
3. **Edit `docs/plans/foundations-rewrite.md`** (3 references).
4. **Edit `docs/plans/specs-designs-cleanup.md`** (1 reference).
5. **Run gates locally:** `kanon verify .`, `python ci/check_links.py`, `python ci/check_foundations.py`, `python ci/check_adr_immutability.py`. The last MUST pass with the `Allow-ADR-edit:` trailer in the commit message.
6. **Commit with the immutability trailer** in the commit message body.
7. **Push, open PR.**

## Acceptance criteria

- [ ] AC-1: Zero remaining `0040.5` references anywhere in `docs/` or `CHANGELOG.md` after the change. Verifiable by `grep -rn "0040\.5" docs/ CHANGELOG.md` returning empty.
- [ ] AC-2: ADR-0048 body says `(0039–0045)` instead of `(0039–0044, plus 0040.5 kernel/reference runtime interface)`.
- [ ] AC-3: Commit message contains the `Allow-ADR-edit: 0048 — ...` trailer with non-empty reason.
- [ ] AC-4: `python ci/check_adr_immutability.py` passes (the trailer authorises the body edit).
- [ ] AC-5: `kanon verify .` returns `status: ok` (zero warnings; regenerate fidelity lock if ADR-0048 SHA changes — though body-edit-only changes likely don't bump the fidelity-tracked spec SHAs).
- [ ] AC-6: `python ci/check_links.py` passes.
- [ ] AC-7: `python ci/check_foundations.py` passes.
- [ ] AC-8: No source / spec / aspect-manifest / protocol-prose / design-doc / foundations-doc changes (only ADR-0048 + CHANGELOG + 2 plans).
- [ ] AC-9: No new CHANGELOG `[Unreleased]` entry; only correction of the existing PR-#50 paragraph.

## Risks / concerns

- **Risk: `check_adr_immutability.py` rejects the trailer for any reason.** Mitigation: the trailer format follows ADR-0032's exact specification (`Allow-ADR-edit: NNNN — <reason>`); reason is non-empty; ADR number is four digits; em-dash separator. If the check fails on a format quibble, fix the trailer and re-commit.
- **Risk: an ADR-0048 fidelity fixture exists and bumps SHA.** Mitigation: ADR-0048 is too new for a fidelity fixture to exist; verify with `ls .kanon/fidelity/` before committing. If a fixture does exist, regenerate the lock as part of this PR.
- **Risk: someone notices the renumbering decision was made unilaterally without panel review.** Mitigation: the renumbering is a mechanical convention-fix, not a design decision; integer-only ADR numbering is established by every prior ADR (0001–0048). Panel review is unnecessary for convention enforcement.

## Documentation impact

- **Touched files:** `docs/decisions/0048-kanon-as-protocol-substrate.md` (1 line, body); `CHANGELOG.md` (1 line, `[Unreleased]` paragraph); `docs/plans/foundations-rewrite.md` (3 lines); `docs/plans/specs-designs-cleanup.md` (1 line).
- **No new files.**
- **No CHANGELOG `[Unreleased]` entry.**
- **No source / spec / aspect-manifest / protocol-prose / design-doc / foundations changes.**
