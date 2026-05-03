---
status: done
shipped-in: PR #92
slug: migration-pr-f-loosen-byte-mirror
date: 2026-05-02
---

# Plan: Migration PR F — Loosen `check_kit_consistency.py` byte-mirror clause (per ADR-0049 D1)

## Goal

Loosen the per-aspect protocols byte-equality enforcement in `scripts/check_kit_consistency.py` from "files must be byte-identical" to "repo-canonical file must exist." Honors ADR-0049 Decision D1 (committed `.kanon/` with byte-mirror clause loosened to behavioural conformance).

## Background

ADR-0049 D1 (vote 5–2) decided to keep `.kanon/` committed AND loosen `ci/check_kit_consistency.py`'s byte-mirror clause to a behavioural conformance test. Today's enforcement at `scripts/check_kit_consistency.py:151-171` requires the per-aspect protocols at `.kanon/protocols/<aspect>/<file>.md` to be byte-identical to `aspects/kanon_<slug>/protocols/<file>.md`. This couples the substrate's self-host tree to the reference-aspect prose source-of-truth in a way that makes single-file edits cost two-file updates.

PR F preserves the existence-check (the repo's `.kanon/protocols/<aspect>/<file>.md` mirror must still exist for each kit-side protocol — that's the self-host probe per ADR-0044) but drops the byte-equality enforcement. ADR-0044 §2 is satisfied by `kanon verify .` exit-0 (behavioural), not by filesystem byte-equality (which was an over-strong invariant invented by `check_kit_consistency.py`'s clause).

## Scope

In scope:
- `scripts/check_kit_consistency.py:151-171`: drop the `kit_proto.read_bytes() != repo_proto.read_bytes()` byte-equality check; preserve the "must exist" check.
- Add a comment explaining the loosening per ADR-0049 D1.

Out of scope:
- The whitelist-driven byte-equality at lines 126-150 (e.g., `docs/sdd-method.md` ↔ kit template). That's a different invariant addressing a different cross-tree relationship; ADR-0049 D1 doesn't comment on it. Defer any review to a future PR.

## Acceptance criteria

- AC1: `scripts/check_kit_consistency.py` no longer enforces byte-equality between `.kanon/protocols/<aspect>/<file>.md` and `aspects/kanon_<slug>/protocols/<file>.md`.
- AC2: It still enforces that each kit-side protocol has a corresponding `.kanon/protocols/<aspect>/<file>.md` mirror file (existence only).
- AC3: 7 standalone gates pass; full pytest passes.
- AC4: A test demonstrating the loosening: edit a `.kanon/protocols/kanon-sdd/<file>.md` to differ from `aspects/kanon_sdd/protocols/<file>.md`; gate exits 0.

## Steps

1. Edit `scripts/check_kit_consistency.py:151-171` to drop byte-equality clause; keep existence check.
2. Update `tests/scripts/test_check_kit_consistency.py` if it asserts on byte-equality.
3. Run gates + pytest.
4. CHANGELOG entry.
5. Commit + push + PR.

## Verification

- `python scripts/check_kit_consistency.py` exits 0 with current state.
- A test demonstrating drift-tolerance (manually: `echo "test" >> .kanon/protocols/kanon-sdd/some-file.md` then re-run gate, exits 0; revert).
- 7 gates → ok; full pytest → 964+ passed.
