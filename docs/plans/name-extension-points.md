---
status: done
design: "Follows ADR-0014 (existing document architecture)"
touches:
  - docs/sdd-method.md
  - src/kanon/kit/aspects/kanon-sdd/files/docs/sdd-method.md
---

# Plan: Name the extension-point convention in sdd-method.md

## Motivation

sdd-method.md has 5 references to "the project-specific
implementation document" or "the project's instantiation doc" without
naming a file convention. An agent or contributor encountering the
file for the first time must already know that a companion
`<project>-implementation.md` exists — the document doesn't tell them.

Naming the convention makes the extension points self-documenting.

## Change

Replace the vague references with a named convention. The intro
paragraph (line 5) establishes the pattern once; downstream references
use the short form.

**Line 5** (intro paragraph) — before:
> Each project defines its own instantiation of the bottom two layers
> (what Implementation and Verification mean concretely). Look for a
> project-specific implementation document alongside this file.

After:
> Each project defines its own instantiation of the bottom two layers
> (what Implementation and Verification mean concretely) in a companion
> document named `<project>-implementation.md` alongside this file.

The 4 downstream references (lines 60, 129, 143, 253) already say
"the project's instantiation doc" or "the project-specific
implementation document" — these are clear enough once the intro
establishes the naming convention. No change needed.

## Files changed

| File | Change |
|------|--------|
| `docs/sdd-method.md` | Edit line 5 intro paragraph |
| `src/kanon/kit/aspects/kanon-sdd/files/docs/sdd-method.md` | Byte-identical copy |

## Acceptance criteria

1. Line 5 names the `<project>-implementation.md` convention.
2. Both copies are byte-identical.
3. `python ci/check_kit_consistency.py` passes.
4. `kanon verify .` passes.
5. No other files modified.
6. The change is project-agnostic — no kanon-brand terms introduced.
