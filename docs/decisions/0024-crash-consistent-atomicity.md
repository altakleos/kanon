---
status: accepted
date: 2026-04-25
---
# ADR-0024: Crash-consistent atomicity for multi-file CLI operations

## Context

The CLI spec (INV-cli-atomicity) originally required "tmp-dir swap" atomicity — the target repo is either in the pre-command or post-command state, never partial. This was ported from Sensei's ADR-0004, which operated on a single managed directory.

kanon's architecture differs: commands write to both `.kanon/` (config, kit.md, protocols, fidelity lock) and the project root (AGENTS.md, harness shims, scaffolded docs). AGENTS.md must remain in the project root because 7 of 8 supported agent harnesses read it natively from that location (ADR-0003). A pointer/indirection pattern was evaluated and rejected — LLM agents do not reliably follow file-chaining instructions across harnesses.

True instantaneous multi-file atomicity is impossible on POSIX when files span multiple directories. `rename(2)` is atomic for a single path; there is no atomic multi-rename syscall. A `.kanon/` directory swap achieves atomicity for that subtree but cannot cover AGENTS.md or harness shims in the project root.

## Decision

Adopt **crash-consistent atomicity** as the CLI's file-safety guarantee:

1. **Per-file atomic writes.** Each file is written via `atomic_write_text()` (write-to-tmp → fsync → `os.replace()` → fsync parent directory). A crash during any single write leaves the original file intact.

2. **Deterministic write ordering.** All commands write `.kanon/` internal files first, root-level files (AGENTS.md, shims) second, and `config.yaml` last. Config.yaml serves as the commit marker — if it reflects the new state, all preceding writes succeeded.

3. **Crash-recovery sentinel.** Before the first write, commands create `.kanon/.pending` (via `atomic_write_text`) containing the operation name and arguments. After the last write, the sentinel is deleted. On entry, every mutating command checks for `.kanon/.pending` — if present, the previous operation was interrupted and is re-executed (all commands are idempotent).

4. **Idempotent commands.** Every mutating command can be re-run safely. `init --force` re-scaffolds, `upgrade` re-renders, `set-depth` skips existing files on increase. This is the recovery mechanism: re-run the interrupted command.

The observable window of partial state is bounded to the duration of the write loop (milliseconds for typical operations on local filesystems). The sentinel ensures this window is self-healing — the next kanon invocation completes the transition before doing anything else.

## Alternatives Considered

**Full directory swap of `.kanon/`.** Write to `.kanon.staging/`, rename `.kanon/` → `.kanon.rollback/`, rename `.kanon.staging/` → `.kanon/`. Achieves atomicity for `.kanon/` contents but does not cover AGENTS.md or harness shims in the project root. Also complicates handling of user state inside `.kanon/` (fidelity.lock, config.yaml timestamps). Rejected: incomplete coverage for higher complexity.

**AGENTS.md as pointer to `.kanon/instructions.md`.** Make AGENTS.md a static file that tells agents to read `.kanon/instructions.md`. All managed content moves inside `.kanon/`, enabling directory-swap atomicity. Rejected: research confirmed that only Claude Code has a deterministic file-include mechanism (`@path` syntax). All other agents (Cursor, Copilot, Windsurf, Cline, Roo Code, JetBrains AI, Kiro) rely on LLM-dependent prose-following to chain files — ~70-80% reliable with strong models, unreliable after context compaction, 0% in autocomplete mode. This trades a real architectural benefit for an unreliable agent experience.

**Write-ahead log (WAL).** Serialize the full operation manifest before writing. Achieves crash-recovery but adds ~80-120 LOC and stores file content hashes — overengineered for a local CLI tool where the recovery model is "re-run the command."

**Symlink swap.** `.kanon/` as a symlink to `.kanon.v<N>/`. Rejected: git tracks symlinks as symlinks, breaking `git diff` and clone behavior. Editors may resolve symlinks inconsistently.

**Amend spec only (no sentinel).** Document per-file atomicity and idempotent recovery without adding the sentinel. Simpler but leaves the recovery model implicit — users must know to re-run the command. The sentinel makes recovery automatic and invisible.

## Consequences

- INV-cli-atomicity is amended to describe crash-consistent atomicity instead of tmp-dir swap.
- `.kanon/.pending` is added to the `.gitignore` template.
- Every mutating CLI command gains a sentinel check at entry (~3 lines per command).
- The recovery guarantee is: after any interruption, the next `kanon` invocation completes the transition before proceeding. No manual intervention required.
- Per-file atomic writes (`_atomic.py`) are unchanged — they remain the foundation.

## References

- ADR-0003 — AGENTS.md is the canonical root; shims are pointers
- ADR-0012 — Aspect model (introduced `aspect` and `fidelity` command groups)
- `docs/specs/cli.md` — CLI surface spec (INV-cli-atomicity)
- `src/kanon/_atomic.py` — atomic write primitive
