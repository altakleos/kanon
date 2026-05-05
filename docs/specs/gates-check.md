---
status: accepted
design: "Follows ADR-0062"
date: 2026-05-04
fixtures_deferred: true
---
# Spec: `kanon gates check`

## Intent

Provide a CLI command that evaluates hard-gate compliance for the current working context. Agents and humans invoke it before source-modifying work to get a definitive pass/fail/judgment verdict per gate, with enough context to act on the result.

## Invariants

- **gates-check-discovery**: The command discovers all active hard gates by reading protocol frontmatter (`gate: hard`) from all enabled aspects, filtered by depth (`depth-min` <= configured aspect depth).
- **gates-check-mechanical**: Gates declaring an optional `check:` field (shell command) are evaluated mechanically. Exit 0 = pass, non-zero = fail.
- **gates-check-judgment**: Gates without a `check:` field return status `"judgment"` with their `question:`, `audit:`, and `skip-when:` fields so the caller can self-evaluate.
- **gates-check-output-json**: The command emits a JSON report to stdout containing per-gate results (`status`, `label`, `aspect`, `check`, `exit_code`, `duration_s`, `question`, `audit`).
- **gates-check-exit-code**: Exit 0 when all gates pass or skip. Exit 1 when any mechanical check fails. Exit 2 on CLI/infrastructure error.
- **gates-check-trace**: Each invocation appends a one-line JSON record to `.kanon/traces/gates.jsonl` (gitignored) for diagnostic tracing.
- **gates-check-publisher-symmetric**: Gate discovery treats kit (`kanon-*`), consumer (`project-*`), and third-party aspects identically. No code-path distinction.
- **gates-check-trust-model**: The `check:` field executes shell commands under the same trust model as `kanon preflight` (ADR-0036: repo write-access is the trust boundary).

## Rationale

Hard gates are enforced via prose (audit-trail sentences in AGENTS.md). Empirical evidence shows agents violate gates after context-window compaction because the prose checklist loses procedural force. A CLI command provides:
1. Externalized state evaluation (the agent doesn't reason about gate status — the CLI tells it)
2. Auditable compliance evidence (command invocation is greppable in transcripts)
3. A complete decision packet (pass/fail/judgment + audit sentence + question) in one output

## Out of Scope

- Replacing the audit-trail sentence mechanism (gates check supplements, not replaces)
- Forcing agents to invoke the command (triggering is the harness's responsibility)
- Evaluating judgment gates mechanically (semantic intent detection is not automatable)
- Integration with `kanon preflight` (separate concern, may be wired later)
- Timeout/retry/parallel execution of check commands (Phase 2)

## CLI Surface

```
kanon gates check <TARGET> [--gate LABEL] [--fail-fast]
kanon gates list <TARGET>
```

## Decisions

- [ADR-0062](../decisions/0062-declarative-hard-gates.md): Gate metadata lives in protocol frontmatter.
