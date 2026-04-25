---
status: deferred
date: 2026-04-25
target-release: v0.3+
realizes:
  - P-specs-are-source
  - P-cross-link-dont-duplicate
serves:
  - vision
fixtures_deferred: "Deferred — depends on `spec-graph-rename.md`'s graph-load primitive landing first; rigorous draft to facilitate promotion later."
---
# Spec: `kanon graph diff` — invariant-level diff between two snapshots

## Intent

Provide a CLI command that renders the difference between two snapshots of the spec graph at the *invariant* level rather than the prose-paragraph level. Reviewers approving spec changes care about invariants added, removed, or modified — not about which adjective changed in a Rationale paragraph. Markdown line-diffs (the `git diff` default) bury the signal under prose churn.

This spec was extracted from the broader `spec-graph-tooling.md` umbrella when that spec was split. It is the long pole of the three (most engineering effort, smallest set of consumers); it stays `status: deferred` while `spec-graph-rename.md` and `spec-graph-orphans.md` ship first. This file exists in draft-grade rigor so that promotion to `status: draft` later requires only a date bump and review, not a rewrite.

## Invariants

<!-- INV-spec-graph-diff-cli-surface -->
1. **CLI surface.** `kanon graph diff <old-rev> <new-rev> [--type <namespace>] [--format json|text]`. `<old-rev>` and `<new-rev>` are git references (sha, tag, branch name, `HEAD~N`); the tool uses `git show <rev>:<path>` to read snapshots. Default `--type` is `spec` (other namespaces' diffs are out of scope for v0.3+; see §Out of Scope). Default `--format` is `text`.

<!-- INV-spec-graph-diff-anchor-keyed -->
2. **Diff is keyed by `INV-*` anchor identity, not bullet ordinal.** This spec depends on `docs/specs/invariant-ids.md` (already accepted). The diff engine extracts `<!-- INV-<spec>-<short-name> -->` anchors from each spec in both snapshots and pairs them by anchor identity. An anchor present in both snapshots with mutated body content renders as `modified`; anchors present in only one render as `added` / `removed`. Bullet ordinal changes (e.g., reordering invariants) without anchor renames produce no spurious diff entries.

<!-- INV-spec-graph-diff-ancestor-required -->
3. **Non-linear histories — old must be ancestor of new, or fail explicitly.** The diff is asymmetric: `<old-rev>` MUST be an ancestor of `<new-rev>` (verified via `git merge-base --is-ancestor`). If not, the command exits 2 with a single-line error naming the two revs and noting the requirement. The rationale: a symmetric "what changed" report on divergent branches misleads — additions and removals on each branch render as a confusing addition/removal pair. Reviewers should diff against a common ancestor, not across branches.

<!-- INV-spec-graph-diff-output-shape -->
4. **Output shape mirrors `kanon verify`.**
    - **Text mode**: human-readable summary grouped by spec, then by change type (added / removed / modified). For modified anchors, a unified-diff fragment of the body content is shown (3 lines context).
    - **JSON mode**: top-level `{"specs": {<spec-slug>: {"added": [<inv-id>], "removed": [<inv-id>], "modified": [{"id": <inv-id>, "before": "...", "after": "..."}]}}, "status": "ok"|"fail"|"warn"}`. Status is "ok" when the diff is empty, "warn" when changes are present but well-formed, "fail" only when the diff itself cannot be computed (malformed snapshot, missing rev).
    - Stdout receives the report, stderr receives operational warnings (e.g., spec deleted in new rev).

<!-- INV-spec-graph-diff-renamed-anchors -->
5. **Renamed anchors are detected when source SHAs match, otherwise reported as remove+add.** If an `INV-foo-bar` anchor in `<old-rev>` corresponds to an `INV-foo-baz` anchor in `<new-rev>` and the body content matches byte-for-byte, the diff renders this as `renamed: INV-foo-bar → INV-foo-baz`. If the body also changed, the diff renders as `removed: INV-foo-bar` + `added: INV-foo-baz` — the tool does not heuristically guess at simultaneous body+name edits. (Anchor renames produced by `kanon graph rename --type inv-anchor` are deterministic and would have a body match; manual edits are not.)

<!-- INV-spec-graph-diff-status-changes -->
6. **Spec-level status transitions are reported.** Frontmatter changes for `status:` (e.g., `draft` → `accepted`, `accepted` → `superseded`) are reported as a top-level entry per spec, separately from invariant-level diffs. Status changes are first-class because a spec going `draft → accepted` is the moment its invariants become load-bearing; reviewers should see this prominently.

<!-- INV-spec-graph-diff-deleted-specs -->
7. **Specs deleted between revs are reported.** A spec present in `<old-rev>` but absent in `<new-rev>` renders as `removed: <spec-slug>`. The reverse (added in new, absent in old) renders as `added: <spec-slug>` with the full new invariant list as `added` entries.

<!-- INV-spec-graph-diff-shared-graph-load -->
8. **Reuses the shared `_graph.py` primitive.** The graph-load function from `spec-graph-rename.md` accepts an optional `git_ref:` parameter; when supplied, file reads are routed through `git show <ref>:<path>` instead of the working tree. This shared primitive is why the diff spec ships after rename + orphans, not before.

<!-- INV-spec-graph-diff-no-mutation -->
9. **Diff is read-only.** The command performs no writes to the working tree, no `.kanon/.pending` sentinel, no fidelity-lock interaction. It can be run on a checked-out branch without disturbing local state.

<!-- INV-spec-graph-diff-empty-input -->
10. **Empty inputs produce empty diff.** If neither snapshot has any specs (e.g., diffing the initial commit against itself, or against a pre-spec-system rev), the output is `{"specs": {}, "status": "ok"}` (text mode: empty grouped report). The command does not error on absent inputs; consumers can pipe to `jq` and check `length`.

## Rationale

**Why anchor-keyed diff is the whole point.** The umbrella spec said "bullet-by-bullet additions/removals." That phrasing was ambiguous — Lens 1 of the panel review noted that without `invariant-ids.md`'s anchors as the primary key, the diff is just `git diff` with extra steps. Pairing by anchor identity (INV-2) lets reordering be invisible while body edits are detected; both behaviors are observably correct.

**Why ancestor-required, not symmetric.** Symmetric diffs across divergent branches mislead reviewers — additions on each branch render as `added` in one direction and `removed` in the other, with no signal that the same conceptual invariant was reworded on both sides. Forcing ancestor → descendant ordering matches how spec changes actually flow (a branch is rebased onto main; main is the ancestor) and rejects the cases that would produce misleading output.

**Why this spec is `deferred` while the others are `draft`.** Per the panel synthesis: rename + orphans together share machinery (~50% reuse of `_graph.py`) and ship the highest-density value. Diff requires git plumbing the codebase doesn't have today (subprocess to `git show`, two-tree parse, anchor-aware diff renderer). The cost differential is ~5-7 sessions for diff alone vs. ~6-7 for rename+orphans together. Holding diff for a separate release is the honest staging.

**Why JSON mode mirrors `kanon verify`.** Consistency across the CLI surface matters for tooling. Both `kanon verify` and `kanon graph orphans` use the same JSON shape (top-level object with `status` and a typed payload); `kanon graph diff` adopts the same convention so a third-party reviewer-tool can call all three with a single parser.

## Out of Scope

- **Diff for non-spec namespaces** (principles, personas, plans, ADRs). v0.3+ is spec-only. ADRs are immutable so a diff is rarely useful; principles change rarely; plans evolve via checkbox state. If demand emerges, a future spec can broaden the namespace coverage.
- **Symmetric / three-way / merge-base diff modes**. Only ancestor → descendant. Tools like `git diff` already serve the symmetric case for prose; this spec serves the structural-invariant case.
- **Diff with working tree as one side**. `<old-rev> WORKING` not supported; user can `git stash` or commit first.
- **Highlighting prose-only changes**. If an invariant's anchor identity is unchanged but only the surrounding prose paragraph changed (not the bullet body), the change is reported as `modified` even though no invariant content moved. Distinguishing "prose-only" from "invariant-content" within a single bullet is out of scope; the body diff in JSON output makes this inspectable.
- **Reviewer tooling integration** (PR-comment-formatted output, GitHub Actions wrappers, etc.). Out of scope; the JSON output is the integration surface.
- **Performance at large repo scale**. The kit has ~25 specs today; diffing two snapshots of 25 specs each is trivial. At 250 specs the cost may matter; revisit then.

## Decisions

- This spec is **status: deferred**. Promotion to `draft` requires no rewrite — the rigor work is done. Promotion is unblocked by `spec-graph-rename.md` shipping its `_graph.py` primitive (INV-8 above) and by demonstrated demand for the diff feature.
- The `git_ref:` parameter on `_graph.py:build_graph` is the architectural commitment that lets diff reuse the rename/orphans machinery; landing rename + orphans first establishes this contract.
- Pattern instantiation under `invariant-ids.md` and `verified-by.md` (already accepted); no new model-level ADR for the diff data shape.
- A small ADR-lite at promotion time captures the ancestor-required (INV-3) and anchor-keyed (INV-2) decisions.
