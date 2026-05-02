---
feature: spec-graph-mvp
serves:
  - docs/specs/spec-graph-rename.md
  - docs/specs/spec-graph-orphans.md
status: done
date: 2026-04-25
target-release: v0.3
---
# Plan: Spec-graph MVP — `kanon graph orphans` + `kanon graph rename`

## Context

The umbrella `spec-graph-tooling.md` was split (PR #21) into three independent specs: `spec-graph-rename.md`, `spec-graph-orphans.md`, and `spec-graph-diff.md`. The first two share an internal primitive — the typed graph-load (`_graph.py` per the rename spec INV-3 / orphans spec INV-8) — and ship in the same release. `spec-graph-diff.md` remains deferred (it depends on this MVP plus `invariant-ids.md`'s anchor backlog being broader).

This plan delivers both `orphans` (read-only report) and `rename` (atomic mutator) atop the shared primitive. Sequencing: build the primitive first; build orphans atop it (read-only, simple correctness); build rename last (high-stakes atomicity, ops-manifest extension to ADR-0024). Each phase produces working code with tests before the next phase begins.

`spec-graph-orphans.md` declares INV-10's "foundation for `consumers-of`" — that future capability rides for free on the primitive but is **not** a v0.3 deliverable.

## Tasks

### Phase 0 — ADR for ops-manifest extension

- [x] T1: Write ADR-0027 documenting the ops-manifest extension to ADR-0024 — captures (a) why a sentinel name alone is insufficient for cross-file rewrite recovery, (b) the `.kanon/graph-rename.ops` schema, (c) the frontmatter-only v0.3 scope, (d) the `--type` requirement → `docs/decisions/0027-graph-rename-ops-manifest.md`. (depends: spec approval)

### Phase 1 — Shared `_graph.py` primitive

- [x] T2: Define typed dataclasses for the graph: `Node(slug, namespace, path, status, frontmatter)`, `Edge(src_slug, dst_slug, kind)`, `GraphData(nodes, edges, by_slug, inbound_index)`. Edge kinds: `realizes`, `serves`, `stressed_by`, `stresses`, `requires`, `inv_anchor` → `src/kanon/_graph.py`. (depends: T1)
- [x] T3: Implement `build_graph(repo_root: Path) -> GraphData` — discovers all foundation, spec, aspect, and capability nodes; parses frontmatter once; populates inbound-edge index; honors `status: deferred`/`superseded` exclusion per orphans-spec INV-3 → `src/kanon/_graph.py`. (depends: T2)
- [x] T4: Unit tests covering node discovery, edge extraction (each edge kind round-trips), inbound-index correctness, and the deferred/superseded exclusion → `tests/unit/test_graph.py`. (depends: T3)

### Phase 2 — `kanon graph orphans`

- [x] T5: Implement `_cmd_graph_orphans(filter_namespace, output_format)` — consumes `build_graph`; computes orphans per orphans-spec INV-2 (no inbound edges per namespace); applies `orphan-exempt:` filtering per INV-5; emits text or JSON per INV-7 → `src/kanon/cli.py`. (depends: T4)
- [x] T6: Wire `kanon graph orphans` Click subcommand with `--type` and `--format` options; group `kanon graph` parent command (rename will be sibling) → `src/kanon/cli.py`. (depends: T5)
- [x] T7: Extend `scripts/check_foundations.py` to validate `orphan-exempt:` requires `orphan-exempt-reason:` (orphans-spec INV-5) → `scripts/check_foundations.py`. (depends: T6)
- [x] T8: Tests: `kanon graph orphans` empty-graph, single-orphan, exempt node, JSON shape, `--type` filter, malformed-graph exits non-zero → `tests/cli/test_graph_orphans.py`. (depends: T7)

### Phase 3 — `kanon graph rename`

- [x] T9: Implement namespace registry — slug-namespace lookup, file-path computation per namespace, edge-source enumeration (which fields/contexts to scan for the slug per namespace) → `src/kanon/_graph.py` extension or new `src/kanon/_rename.py`. (depends: T4)
- [x] T10: Implement token-boundary matchers for each context — frontmatter scalars/lists/keys, markdown link targets `](...)`, `INV-` anchors, AGENTS.md markers (reuses `_iter_markers` from PR #2), explicit fenced-code-block skip → `src/kanon/_rename.py`. (depends: T9)
- [x] T11: Implement collision detection (rename-spec INV-10) — refuses if the target slug already exists in the namespace; error names colliding artifact path → `src/kanon/_rename.py`. (depends: T10)
- [x] T12: Implement ops-manifest writer — `.kanon/graph-rename.ops` JSON `{old, new, type, files: [...], rendered: {<rel>: <sha256>}}`; `.kanon/.pending` sentinel `graph-rename`; `_OP_GRAPH_RENAME = "graph-rename"` constant; `_PENDING_OP_TO_COMMAND` mapping update → `src/kanon/cli.py`, `src/kanon/_rename.py`. (depends: T11)
- [x] T13: Implement atomic-rewrite engine — for each target file, compute post-rename content; write via `_atomic.atomic_write_text`; preserves byte-equality kit-mirror twins per rename-spec INV-5 → `src/kanon/_rename.py`. (depends: T12)
- [x] T14: Implement post-rewrite CI fleet self-check — runs `check_foundations`, `check_invariant_ids`, `check_verified_by`, `check_links`, `check_kit_consistency`, and `kanon verify .` against the renamed tree before clearing the sentinel; on failure, sentinel persists and the operation reports the rejecting check (rename-spec INV-4) → `src/kanon/_rename.py`. (depends: T13)
- [x] T15: Implement crash-recovery — `_check_pending_recovery` reads `.kanon/graph-rename.ops`; re-running with same args completes the operation idempotently (rename-spec INV-3, INV-7) → `src/kanon/cli.py`. (depends: T14)
- [x] T16: Implement `--dry-run` — emits `{path, before-line, after-line}` plan to stdout; writes neither sentinel nor ops-manifest (rename-spec INV-6) → `src/kanon/_rename.py`. (depends: T13)
- [x] T17: Implement post-rename advisories — fidelity-lock-stale advisory (INV-9) and prose-mention-locations advisory (INV-2 fence-aware skip context) → `src/kanon/_rename.py`. (depends: T15)
- [x] T18: Wire `kanon graph rename` Click subcommand: `--type`, positional `<old> <new>`, `--dry-run` → `src/kanon/cli.py`. (depends: T17)
- [x] T19: Tests: per-namespace happy path (principle, persona, spec, aspect, capability, inv-anchor, adr); collision rejection; `--dry-run`; crash-recovery (interrupt then re-run); CI-fleet self-check rejection; byte-equality kit-mirror coverage; fenced-code-block skip; non-ASCII slug rejection at boundary → `tests/cli/test_graph_rename.py`. (depends: T18)
- [x] T20: Synthetic failure tests for the recovery path — monkeypatch crash points after ops-manifest write and before sentinel clear → `tests/cli/test_graph_rename_recovery.py`. (depends: T19)

### Phase 4 — Documentation and release wiring

- [x] T21: Promote both specs `status: draft` → `status: accepted (lite)` once T19 and T8 are green; populate `invariant_coverage:` mapping each INV anchor to the test that exercises it → `docs/specs/spec-graph-rename.md`, `docs/specs/spec-graph-orphans.md`. (depends: T19, T8)
- [x] T22: Update `docs/plans/roadmap.md` — flip both specs from "Drafted for v0.3 (work in flight)" to "Shipped (v0.3.0aN)" once released; leave `spec-graph-diff` in the v0.3+ deferred row. (depends: T21)
- [x] T23: Add CHANGELOG entry under `## [Unreleased]` — `feat: kanon graph orphans` and `feat: kanon graph rename` with brief one-liners and ADR-0027 reference → `CHANGELOG.md`. (depends: T19, T8)
- [x] T24: Update README aspects-table or feature list to mention `kanon graph` if user-facing surface warrants it; otherwise None → `README.md` (only if needed). (depends: T23)
- [x] T25: Refresh `.kanon/fidelity.lock` for the two specs once they reach `accepted (lite)` → `.kanon/fidelity.lock`. (depends: T21)

## Acceptance Criteria

- [x] AC1: Every invariant in `spec-graph-rename.md` (INV-1..INV-10) is exercised by at least one test in `tests/cli/test_graph_rename*.py` and recorded in `invariant_coverage:`.
- [x] AC2: Every invariant in `spec-graph-orphans.md` (INV-1..INV-10) is exercised by at least one test in `tests/cli/test_graph_orphans.py` and recorded in `invariant_coverage:`.
- [x] AC3: `kanon graph rename --type principle <existing> <new> --dry-run` emits a plan and exits 0 without modifying the tree (sentinel-free, ops-manifest-free).
- [x] AC4: `kanon graph rename --type principle <existing> <new>` (no `--dry-run`) leaves the tree such that the full CI fleet (`check_foundations`, `check_invariant_ids`, `check_verified_by`, `check_links`, `check_kit_consistency`, `kanon verify .`) returns exit 0.
- [x] AC5: Killing the rename process after ops-manifest write but before sentinel clear, then re-invoking the same command, completes the rename idempotently and clears the sentinel.
- [x] AC6: `kanon graph orphans` on the kanon repo itself emits `status: ok` and a stable text/JSON shape; `--format json` output matches the schema described in orphans-spec INV-7.
- [x] AC7: `pytest -q` and `ruff check` pass; coverage stays at or above the configured floor.
- [x] AC8: `kanon verify .` returns ok against the post-merge main.

## Out of Scope (deferred)

- **Prose-mention rewriting** — rename-spec out-of-scope; emitted as advisory only.
- **Fidelity-lock auto-update** — rename-spec out-of-scope; advisory only.
- **`--force` collision override** — rename-spec out-of-scope.
- **`kanon graph diff`** — separate deferred spec; depends on this MVP's primitive plus `invariant-ids.md` backlog.
- **`consumers-of <slug>` query** — orphans-spec INV-10 says the data structure is ready; the CLI verb belongs to a separate spec accompanying `expand-and-contract-lifecycle` promotion.
- **`--fail-on-orphan` flag** — orphans-spec out-of-scope; consumers gate via `jq` over JSON.
- **Aspect-rename consumer migration** — rename-spec out-of-scope; v0.3 ships only the in-repo rename mechanic.
- **Cross-worktree coordination during rename** — out of scope; rename touches only the invoking worktree.
- **Cycle detection in the graph** — orphans-spec out-of-scope.

## Documentation Impact

- New CLI surface: `kanon graph orphans` and `kanon graph rename`. Update CLI help text, `kanon --help` top-level grouping, and any `docs/kanon-implementation.md` CLI summary.
- New ADR-0027 (ops-manifest extension); add to `docs/decisions/README.md` index.
- `CHANGELOG.md` `## [Unreleased]` entries for both commands.
- `docs/plans/roadmap.md` row updates once shipped.
- Spec promotions: both specs flip `draft` → `accepted (lite)` with `invariant_coverage:` populated.
- README mention only if the v0.3 release notes feature `kanon graph` prominently; otherwise no change.
