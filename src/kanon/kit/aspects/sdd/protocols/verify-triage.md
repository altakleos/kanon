---
status: accepted
date: 2026-04-22
depth-min: 1
invoke-when: A `kanon verify` run returns a non-ok status, or the user asks "what does this verify report mean?"
---
# Protocol: Verify-triage

## Purpose

Turn a `kanon verify` JSON report into a prioritized, human-readable action list. The report emits a flat array of `errors` and `warnings`; left un-triaged they look like a wall of text. This protocol sorts them into blockers → config drift → content drift → warnings, and proposes fixes — without executing any of them until the user approves.

## Steps

### 1. Parse the report

Read the most recent `verify` output (stdout). Extract the JSON object. For each `errors[i]` entry, classify into one of four buckets:

- **Structural (S)** — missing required files/directories. Pattern: `missing required file: <rel>`, `missing required directory: <rel>`.
- **Marker (M)** — AGENTS.md marker-pair imbalance or missing tier-expected section. Pattern: `AGENTS.md missing marker pair for section '<name>'`, `AGENTS.md marker imbalance: N begin(s), M end(s)`.
- **Config (C)** — `.kanon/config.yaml` invalid or missing fields. Pattern: `Not a kanon project:`, `config.tier is <n>; must be one of […]`.
- **Model-drift (D)** — anything else the verifier flagged (e.g., content mismatches once those checks land). If unsure, classify as D and flag for user judgment.

Also bucket each `warnings[i]` as warning-severity regardless of pattern.

### 2. Collect context

Before proposing fixes, read:

- **`.kanon/config.yaml`.** What tier is declared? When was `tier_set_at`? What `kit_version` is installed?
- **Git log, last 10 commits touching `.kanon/` or `AGENTS.md`.** Recent churn hints at whether the drift is from a just-ran `tier set`, a manual edit, or a long-standing gap.
- **AGENTS.md.** Eyeball it if any M-class errors exist — are markers actually missing, or just their content stripped? Line numbers help the user.

### 3. Prioritize

Output order is:

1. **C-class errors first.** A broken config makes every subsequent check spurious. If config says `tier: 7`, none of the tier-1 section checks mean anything.
2. **S-class errors second.** Missing required files. These are usually single-line fixes: `kanon init --force`, or `cp` from the kit, or `kanon tier set <N>` (if the file exists at a different tier).
3. **M-class errors third.** Marker imbalances. Often caused by a user editing AGENTS.md and accidentally deleting half a marker pair.
4. **D-class errors fourth.** Uncertain territory — prefer routing to the user.
5. **Warnings last.** Report but don't act unless the user asks.

### 4. Propose fixes

For each finding (in the order above), draft a fix proposal:

- **What would change.** Concrete path(s) and a one-line description.
- **Command to run.** The exact `kanon` invocation, `cp`/`mv`/`rm` command, or AGENTS.md edit.
- **Reversibility.** Is the fix destructive? (Usually no — the kit is non-destructive by design.)
- **Confidence.** High / medium / low. Low-confidence fixes especially for D-class go to the user unrun.

### 5. Halt before mutating

**Never execute the proposed fixes yourself.** Present the prioritized list to the user with the exact commands. The user — or a subsequent tool-use turn after explicit approval — executes.

Exception: if a single finding is a clear, trivial fix (e.g., a single file needs to be copied from the kit to the target) AND the user has already confirmed they want you to proceed, you may execute *that one* and report.

### 6. Route unresolvable findings

If a finding resists classification, or the fix is outside `kanon`'s scope (e.g., "your AGENTS.md preamble has a typo in a section header"), escalate: describe the issue, say what you looked for, and ask the user how to proceed.

## Exit criteria

You have produced a ranked list of proposed fixes (with commands and confidence), or explicitly routed unresolvable findings to the user. No filesystem has been mutated.

## Anti-patterns

- **Running fixes first, triaging later.** The triage IS the output.
- **Executing `--force` flags.** If the fix requires `--force`, that's a human judgment call.
- **Hiding D-class findings.** Uncertainty deserves surfacing, not quiet omission.
