---
status: accepted (lite)
date: 2026-04-25
target-release: v0.3
realizes:
  - P-cross-link-dont-duplicate
  - P-self-hosted-bootstrap
serves:
  - vision
fixtures:
  - tests/test_graph_rename.py
  - tests/test_graph.py
invariant_coverage:
  INV-spec-graph-rename-cli-surface:
    - tests/test_graph_rename.py::test_inv1_type_required
    - tests/test_graph_rename.py::test_inv1_invalid_type_lists_seven
    - tests/test_graph_rename.py::test_inv1_valid_namespace_accepted
  INV-spec-graph-rename-match-semantics:
    - tests/test_graph_rename.py::test_inv2_token_boundary_does_not_match_substring
    - tests/test_graph_rename.py::test_principle_rename_rewrites_link_target
  INV-spec-graph-rename-atomicity:
    - tests/test_graph_rename.py::test_inv3_ops_manifest_cleared_on_success
    - tests/test_graph_rename.py::test_inv3_idempotent_rerun_after_success
    - tests/test_graph_rename.py::test_inv3_recovery_completes_partial_rename
    - tests/test_graph_rename.py::test_check_pending_recovery_auto_replays_graph_rename
    - tests/test_graph_rename.py::test_ops_manifest_records_full_content
  INV-spec-graph-rename-dry-run:
    - tests/test_graph_rename.py::test_inv6_dry_run_writes_no_files
    - tests/test_graph_rename.py::test_dry_run_via_function_returns_status
    - tests/test_graph_rename.py::test_format_dry_run_empty_rewrites
  INV-spec-graph-rename-recovery-message:
    - tests/test_graph_rename.py::test_inv7_recovery_message_command_form
  INV-spec-graph-rename-collision-detection:
    - tests/test_graph_rename.py::test_inv10_collision_refuses
  INV-spec-graph-rename-aspect-rename-special-case:
    - tests/test_graph_rename.py::test_inv8_aspect_namespace_raises_not_implemented
---
# Spec: `kanon graph rename` — atomic slug rename across the cross-link graph

## Intent

Provide a single CLI command that renames a slug across every artifact that references it — frontmatter values, INV-* anchors, AGENTS.md markers, markdown link targets — atomically per ADR-0024. Sensei's experience shows manual rename via `grep -r` + 10+ hand-edits leaves silent inconsistencies; this spec replaces that workflow with a tool that either completes the rename fully or leaves the repo in a state where a re-run completes it.

This spec was extracted from the broader `spec-graph-tooling.md` umbrella when that spec was split; the orphan-detection and invariant-diff capabilities live in their own specs (`spec-graph-orphans.md`, `spec-graph-diff.md`).

## Slug namespaces

The kit has seven slug namespaces. The rename command treats each as a distinct address space and requires the caller to name which namespace is being renamed:

| Namespace | Lives in | Example | Edge sources |
|---|---|---|---|
| `principle` | `docs/foundations/principles/<slug>.md` | `P-prose-is-code` | spec `realizes:`, prose mentions in plans |
| `persona` | `docs/foundations/personas/<slug>.md` | `solo-engineer` | spec `stressed_by:`, persona `stresses:` |
| `spec` | `docs/specs/<slug>.md` (filename stem) | `aspect-config` | plan `serves:` (in prose / frontmatter), `INV-<spec>-*` anchor prefixes |
| `aspect` | `src/kanon/kit/manifest.yaml` aspects key + `src/kanon/kit/aspects/<name>/` directory | `worktrees` | `requires:` depth-predicates, `provides:` capability owner aspect, AGENTS.md `<!-- kanon:begin:<aspect>/* -->` markers, consumer `.kanon/config.yaml` `aspects.<name>:` |
| `capability` | top-manifest `provides:` lists | `planning-discipline` | `requires:` capability-presence predicates |
| `inv-anchor` | `<!-- INV-<spec>-<short-name> -->` HTML comments and matching `invariant_coverage:` map keys | `INV-aspect-config-yaml-scalar-parsing` | spec body anchors, `invariant_coverage:` keys |
| `adr` | `docs/decisions/<NNNN>-<slug>.md` filename | `0024-crash-consistent-atomicity` | prose mentions in specs/ADRs/CHANGELOG; `supersedes:`/`superseded-by:` frontmatter once those edges are formally typed |

## Invariants

<!-- INV-spec-graph-rename-cli-surface -->
1. **CLI surface.** `kanon graph rename --type <namespace> <old-slug> <new-slug> [--dry-run]`. The `--type` argument is required; auto-detection is explicitly out of scope (collision risk between namespaces is too high — e.g., a bare token `worktrees` could refer to the spec, the aspect, or the directory). `<namespace>` must be one of `principle`, `persona`, `spec`, `aspect`, `capability`, `inv-anchor`, `adr`. Any other value is a single-line error naming the offending token and the seven valid options.

<!-- INV-spec-graph-rename-match-semantics -->
2. **Match semantics — token-boundary, not substring.** The rename engine matches occurrences of `<old-slug>` as a complete token in the contexts it scans:
    - **Frontmatter values** (YAML scalars, list items, mapping keys for `invariant_coverage:`): the slug must equal the entire scalar / list item / key, not a substring. `realizes: [P-foo, P-foo-bar]` renaming `P-foo` → `P-baz` produces `realizes: [P-baz, P-foo-bar]`, never `[P-baz, P-baz-bar]`.
    - **Markdown link targets** (`](path/<old-slug>.md)` or `](path/<old-slug>.md#anchor)`): the slug must occupy the entire path segment.
    - **`INV-*` anchors**: matched against the full anchor name pattern `INV-<old-slug>-<short-name>`; the leading `INV-` and trailing `-<short-name>` are preserved when the namespace is `spec` (a spec-slug rename also rewrites every `INV-` anchor it owns).
    - **AGENTS.md markers**: `<!-- kanon:begin:<old-slug>/<section> -->` and matching `end` markers, namespace-prefixed per `_iter_markers` (the line-anchored, fence-aware matcher from PR #2). Bare-token matches inside fenced code blocks (``` or `~~~`) are explicitly NOT rewritten.
    - **Prose**: out of scope for v0.3 (see §Out of Scope). The tool emits a post-rename advisory listing locations that look like prose mentions of the slug for the user to inspect manually.

<!-- INV-spec-graph-rename-atomicity -->
3. **Crash-consistent atomicity per ADR-0024 + ops-manifest extension.** Before any file is rewritten, the tool writes an ops-manifest at `.kanon/graph-rename.ops` containing `{old, new, type, files: [<rel-path>], rendered: {<rel-path>: <sha256>}}` plus a `.kanon/.pending` sentinel labeled `graph-rename`. Each target file is written via `_atomic.atomic_write_text`. After the last write the ops-manifest is deleted and the sentinel cleared. If the process is interrupted, the next CLI invocation that reads the sentinel sees `graph-rename` pending; re-running `kanon graph rename` with the same arguments reads the ops-manifest, computes the expected post-rename content for each unwritten file, and completes the operation. The ops-manifest extends — does not replace — the ADR-0024 contract: per-file writes remain individually atomic, and the manifest is the recovery state for cross-file consistency that a single sentinel name cannot encode.

<!-- INV-spec-graph-rename-postcondition -->
4. **Postcondition: the kit's CI fleet passes.** After a successful rename, the following all return exit 0 against the renamed repo: `python ci/check_foundations.py`, `python ci/check_invariant_ids.py`, `python ci/check_verified_by.py`, `python ci/check_links.py`, `python ci/check_kit_consistency.py`, `kanon verify .`. The tool runs this fleet as a self-check before clearing its sentinel; if any check fails, the sentinel persists and the operation reports which check rejected the rename.

<!-- INV-spec-graph-rename-byte-equality -->
5. **Byte-equality boundary handling.** Files in the kit-bundle byte-equality whitelist (declared per-aspect in `src/kanon/kit/aspects/<name>/manifest.yaml` under `byte-equality:` per ADR-0011) have a kit-side mirror at `src/kanon/kit/aspects/<name>/files/<rel>`. When the rename touches a repo-canonical file with a kit mirror, both copies are rewritten together in the same ops-manifest run; INV-3's atomicity covers them as a single transaction.

<!-- INV-spec-graph-rename-dry-run -->
6. **`--dry-run` is mandatory infrastructure.** With `--dry-run`, the tool emits the ops-manifest contents to stdout (one line per `{path, before-line, after-line}` pair) and exits 0 without writing anything. No `.kanon/.pending` sentinel is written; no `.kanon/graph-rename.ops` file is created. Users can review the planned change before committing to it.

<!-- INV-spec-graph-rename-recovery-message -->
7. **Recovery message names the right command.** When `_check_pending_recovery` detects a `graph-rename` sentinel, the warning suggests `kanon graph rename` (with a space, matching the `_PENDING_OP_TO_COMMAND` convention added in PR #18). The internal sentinel string is exposed as `_OP_GRAPH_RENAME = "graph-rename"`.

<!-- INV-spec-graph-rename-aspect-rename-special-case -->
8. **Aspect rename is the most consequential case.** Renaming an aspect (`<namespace> = aspect`) touches: the top-manifest `aspects:` mapping, the per-aspect sub-manifest path, every kit file under `aspects/<name>/`, every consumer-facing `.kanon/protocols/<name>/` reference (in repo and in kit), every `requires: ["<name> >= N"]` predicate in other aspects' sub-manifests, every AGENTS.md marker prefixed `<!-- kanon:begin:<name>/<section> -->`, the `aspects.<name>:` key in the repo's own `.kanon/config.yaml`, and every prose mention in plans referring to the aspect. The tool must enumerate all of these. Renaming an aspect that any *consumer* has enabled is not rolled back automatically — consumers re-discover the rename on the next `kanon upgrade` (the upgrade migration story for renamed aspects is out of scope for v0.3).

<!-- INV-spec-graph-rename-fidelity-lock -->
9. **Fidelity lock interaction.** A successful rename leaves the lock at `.kanon/fidelity.lock` stale (the post-rename file SHAs differ from the locked SHAs). The tool emits a single-line advisory pointing at `kanon fidelity update`. Auto-update is explicitly NOT performed in v0.3 — the rename and the lock refresh remain separate user-controlled steps so the lock-update step retains its own audit trail.

<!-- INV-spec-graph-rename-collision-detection -->
10. **Collision detection.** Before writing the ops-manifest, the tool checks that `<new-slug>` does not already exist in the target namespace (e.g., a `principle` rename refuses if `docs/foundations/principles/<new>.md` already exists). The error names the colliding artifact path. The CLI offers no `--force` override; collisions must be resolved manually.

## Rationale

**Why a `--type` argument is required, not auto-detected.** Auto-detection by where the slug currently lives appears tempting: a bare `worktrees` could be looked up in `principles/`, `personas/`, `specs/`, `manifest.yaml`. The seven namespaces overlap in shape — `worktrees` is currently both an aspect *and* a (would-be) capability `worktree-isolation`'s implicit producer. Forcing the caller to declare the namespace makes the rename's intent explicit in the audit trail and eliminates a class of "tool guessed wrong" bugs.

**Why ops-manifest, not just sentinel + idempotent re-run.** Every other mutating CLI command (`init`, `upgrade`, `aspect set-depth`, etc.) has `config.yaml` as a natural commit marker — the file is written last and reflects the new state. `graph rename` has no equivalent marker; the rewrite target set is open-ended (every file containing the old slug). The ops-manifest captures the rewrite plan so a re-run after partial completion can complete it idempotently. The manifest is the smallest extension to the ADR-0024 model that closes this gap.

**Why frontmatter-only in v0.3.** Prose-mention rewriting requires a context-aware matcher (a slug appearing in a sentence inside a paragraph is sometimes a reference to be updated, sometimes an illustrative example to be left alone). The tool produces a post-rename advisory listing prose locations for manual review; a future spec can promote prose handling once the pattern is proven for frontmatter and structured locations.

**Why CI fleet is the postcondition, not just `check_foundations.py`.** The umbrella spec named only one validator. In practice, INV anchors are checked by `check_invariant_ids.py`, invariant-coverage by `check_verified_by.py`, link integrity by `check_links.py`, byte-equality by `check_kit_consistency.py`. A rename that passes one but fails another is a broken rename. Naming the full fleet makes the postcondition machine-checkable.

## Out of Scope

- **Prose-mention rewriting** — out of scope for v0.3. The tool emits an advisory listing prose locations; user inspects and edits manually. A future spec may revisit.
- **Fidelity-lock auto-update** — out of scope. Rename ends with an advisory, not a mechanical lock refresh.
- **`--force` to override collisions** — not provided. Collision is an error; the user resolves it.
- **Auto-detection of `<namespace>`** — not provided. CLI requires explicit `--type`.
- **Rename across non-current branches / git history** — out of scope. The tool operates on the working tree only; CHANGELOG entries and historical plans are NOT rewritten (preserving historical record).
- **Rename inside fenced code blocks** — explicitly skipped. Documentation that quotes a slug as illustration is preserved.
- **Renaming an aspect that consumer projects have enabled** — out of scope as a managed migration. The spec ships the in-repo rename mechanic; the consumer-side migration is a future spec.
- **Worktree coordination** — when other worktrees of the same repo exist, the rename touches only the invoking worktree's tree. Other worktrees may be left inconsistent.

## Decisions

- New ADR-lite captures (a) the ops-manifest extension to ADR-0024, (b) the `--type` requirement, and (c) the frontmatter-only v0.3 scope.
- Pattern instantiation under ADR-0011 (kit-bundle byte-equality) and ADR-0024 (atomic writes); no new model-level ADR for the data shape itself.
- Specifies INV-3 in terms of ADR-0024 vocabulary verbatim — does not invent a parallel atomicity language.
