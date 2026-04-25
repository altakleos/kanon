---
status: accepted (lite)
date: 2026-04-25
weight: lite
---
# ADR-0027: Ops-manifest extension to ADR-0024 for `kanon graph rename`

## Decision

`kanon graph rename` extends the ADR-0024 crash-consistent-atomicity contract with a per-operation **ops-manifest** at `.kanon/graph-rename.ops`. The manifest is written before any target file is rewritten and contains:

```json
{
  "old": "<old-slug>",
  "new": "<new-slug>",
  "type": "<namespace>",
  "files": ["<rel-path>", ...],
  "rendered": {"<rel-path>": "<sha256>"}
}
```

The `.kanon/.pending` sentinel labels the operation `graph-rename`. Per-file writes still use `_atomic.atomic_write_text` (unchanged from ADR-0024). After the last file is rewritten and the post-rewrite CI fleet self-check passes, the ops-manifest is deleted and the sentinel is cleared.

If the process is interrupted at any point after the ops-manifest is written:

1. The next mutating CLI invocation reads the sentinel, sees `graph-rename` pending.
2. Re-running `kanon graph rename --type <ns> <old> <new>` reads the ops-manifest, recomputes the expected post-rename content for each file in `files`, and writes any whose current SHA does not match the `rendered` entry.
3. Recovery is idempotent — files already at the post-rename state are skipped.

The ops-manifest also constrains the public CLI: rename requires an explicit `--type <namespace>` argument; auto-detection is rejected (the seven slug namespaces overlap in shape — see `spec-graph-rename.md` Rationale). Recovery is similarly bound by the manifest's `type` field, so a re-run that names a different `--type` is rejected as a different operation.

The v0.3 scope is **frontmatter and structured locations only** (frontmatter scalars, markdown link targets, `INV-` anchors, AGENTS.md markers). Prose-mention rewriting is deferred; the tool emits an advisory listing prose locations instead.

## Why

Every other mutating CLI command (`init`, `upgrade`, `aspect set-depth`, `aspect set-config`, etc.) has `config.yaml` as a natural commit marker — the file is written last and reflects the new state, so a single sentinel name is sufficient for recovery (re-run the same command and it skips the work already done). `graph rename` has no equivalent marker: the rewrite target set is open-ended (every file containing the old slug across seven namespaces) and there is no single file whose post-rewrite content encodes "rename complete." A sentinel labeled `graph-rename` alone tells the recovery code an operation was interrupted but cannot tell it *which* rename — old/new slug pair, namespace, file set — and a second invocation with different arguments is structurally indistinguishable from the original. The ops-manifest captures the rewrite plan so a re-run after partial completion can complete *the original operation* idempotently, even if the user has forgotten the exact arguments.

The manifest is the smallest extension to the ADR-0024 model that closes this gap. It does not replace per-file atomic writes; it composes with them as a cross-file consistency layer that a single sentinel name cannot encode. The choice to require explicit `--type` (rather than auto-detect from slug shape) keeps the manifest's `type` field unambiguous and makes the user's rename intent legible in the audit trail.

The frontmatter-only v0.3 scope reflects the same principle: prose-mention rewriting needs context-aware matching (a slug appearing in a sentence may be a reference to update or an illustrative example to leave alone). Rather than ship a heuristic that occasionally rewrites the wrong thing, v0.3 ships an advisory listing prose locations and lets the user inspect them. A future spec can promote prose handling once the structured-location pattern is proven.

## Alternative

**Sentinel-only recovery (no ops-manifest).** Treat `graph-rename` as a flag and require the user to re-pass the original arguments. Rejected: a partially-completed rename leaves the repo with some files at the new slug and some at the old, so a stale `git status` does not preserve the rename intent. Forcing the user to remember `--type` plus the old/new slugs across an interruption is a recovery model that depends on user memory; the manifest preserves the intent on disk.

**Write-ahead log of full file contents.** Store every file's pre- and post-rewrite content in the manifest. Rejected: bloats the manifest from kilobytes to megabytes for typical aspect renames, duplicates content already on disk and in git history, and adds checksumming overhead with no recovery benefit beyond what the SHA-keyed `rendered` map already provides.

**Single sentinel containing CLI-args JSON.** Encode the operation arguments inside the existing `.kanon/.pending` file rather than introducing a sibling manifest. Rejected: blurs the recovery protocol — every other command's sentinel contents are a free-form label, and parsing JSON from one specific command's sentinel forks the contract. A separate file is clearer.

**Auto-detect `<namespace>` from slug shape.** Look up the slug in `principles/`, `personas/`, `specs/`, etc., and infer the namespace. Rejected: the seven namespaces overlap in shape (a bare token like `worktrees` could refer to the spec, the aspect, or an implicit capability), and the inference would silently rewrite the wrong target. Forcing `--type` makes intent explicit.

## References

- [ADR-0024](0024-crash-consistent-atomicity.md) — the base contract this extends.
- [ADR-0011](0011-kit-bundle-refactor.md) — kit-bundle byte-equality, which the rewrite engine must honor (rename-spec INV-5).
- [`docs/specs/spec-graph-rename.md`](../specs/spec-graph-rename.md) — the contract this implements.
- [`docs/specs/spec-graph-orphans.md`](../specs/spec-graph-orphans.md) — sibling spec sharing the `_graph.py` primitive.
