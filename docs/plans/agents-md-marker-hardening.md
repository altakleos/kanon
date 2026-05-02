---
feature: agents-md-marker-hardening
serves: docs/specs/cli.md
design: "Follows ADR-0003 (AGENTS.md is canonical root) — pattern instantiation; no new mechanism."
status: done
date: 2026-04-25
---
# Plan: Harden AGENTS.md marker handling against user-content collisions

## Context

The audit (Risk R1) found that `_scaffold.py:268-371` locates kanon-managed sections in `AGENTS.md` with raw `text.find("<!-- kanon:begin:...")`. This is unsafe in two ways:

1. **Quoted markers in user content.** A user (or a kit-shipped doc) that quotes a marker string inside an indented paragraph, an inline-code span, or a fenced code block — for example, an ADR explaining how the marker system works — can be mistaken for a real marker. On the next `kanon upgrade` or `aspect set-depth`, the merge logic would mis-identify section bounds and either replace the wrong region or drop user content.

2. **No line anchoring.** The current matcher accepts a marker that follows arbitrary text on the same line (e.g., `> <!-- kanon:begin:sdd/foo -->` inside a blockquote). A correctly-formed kit-managed marker is always emitted by `_insert_section` on a line of its own (`_scaffold.py:298-309`), so line-anchoring is an enforceable invariant.

The fix preserves all current behaviour for well-formed input (the kit's own AGENTS.md round-trips byte-identically through the new matcher) and changes behaviour only on adversarial input where corruption is the alternative.

## Tasks

- [x] T1: Added `_MARKER_RE`, `_FENCE_RE`, `_fenced_ranges`, `_iter_markers`, and `_find_section_pair` to `src/kanon/_manifest.py` (the dependency root). Markers must occupy a line by themselves; tabs/spaces around them are tolerated; matches inside fenced code blocks (``` or `~~~`, balanced) are skipped.
- [x] T2: `_replace_section`, `_remove_section`, `_merge_agents_md`, and `_rewrite_legacy_markers` in `src/kanon/_scaffold.py` now call `_find_section_pair` / `_iter_markers`. `_insert_section` left unchanged — it constructs new content rather than parsing existing markers. Substitutions are line-aligned.
- [x] T3: `_replace_section` runs from the end of the begin-marker line to the start of the end-marker line. Round-trip property verified by `test_assembled_agents_md_is_merge_fixed_point` and `test_repo_agents_md_round_trips`.
- [x] T4: `check_agents_md_markers` in `src/kanon/_verify.py` now uses `_find_section_pair` for presence and `_iter_markers` for the balance count.
- [x] T5: `scripts/check_kit_consistency.py` imports `_iter_markers` from `kanon._manifest` (with a `sys.path.insert` so the script remains runnable from a fresh clone). The local `_SECTION_RE` literal is gone.
- [x] T6: `tests/test_scaffold_marker_hardening.py` covers all five sub-cases plus inline-prefix and balance-counter checks. 8 tests, all passing.
- [x] T7: `test_repo_agents_md_round_trips` asserts the repo's own AGENTS.md is a fixed point of `merge(existing, assemble(...))`. Passes.
- [x] T8: `CHANGELOG.md` `## [Unreleased] / ### Fixed` carries the entry.

## Acceptance Criteria

- [x] AC1: `pytest` passes — 313 passed, 5 deselected (e2e), 93.03% coverage.
- [x] AC2: `tests/test_scaffold_marker_hardening.py::test_quoted_marker_in_backtick_fence_is_ignored` (and 7 sibling cases) pass. (Renamed from `test_quoted_marker_in_fenced_block_is_ignored` to be specific about delimiter; tilde-fence has its own test.)
- [x] AC3: `uv run kanon verify .` against the worktree returns `status: ok` (warnings are stale-fidelity-lock entries, unrelated to this change).
- [x] AC4: `python scripts/check_kit_consistency.py` returns exit 0.
- [x] AC5: Marker primitives live solely in `kanon._manifest`; `_scaffold.py`, `_verify.py`, and `scripts/check_kit_consistency.py` import them. No regex literals duplicated across the three.

## Documentation Impact

- `CHANGELOG.md`: one-line entry under `## [Unreleased] / ### Fixed` (T8).
- No spec amendment: the change preserves observable behavior on well-formed input. ADR-0003 already governs AGENTS.md as the canonical root; no new decision is recorded.
- No README change: the marker syntax users see in their AGENTS.md is unchanged; only the parser is hardened.
