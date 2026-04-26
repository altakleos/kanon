---
status: accepted
date: 2026-04-24
depth-min: 1
invoke-when: An agent is about to declare a plan or task complete, or the user asks "is this done?"
---
# Protocol: Completion checklist

## Purpose

Verify that work is actually done before declaring it complete. LLM agents tend to declare victory after the happy path works, skipping edge cases, documentation, and cross-cutting concerns. This checklist catches the gaps.

## Steps

### 1. Plan acceptance criteria

- Re-read the plan's `## Acceptance Criteria` section.
- For each criterion: is there evidence it's satisfied? (test output, file exists, command succeeds)
- If any criterion is unmet, the work is not done.

### 2. Test delta

- Were any tests deleted? If so, what now covers the behavior they protected?
- Were any assertions weakened (expected values changed)? If so, why was the old value wrong?
- Were new tests added for new behavior?
- Does the test suite pass?

### 3. Documentation impact

- Does the plan have a `## Documentation Impact` section?
- If it lists docs to update, were they updated?
- If behavior changed, does the README still accurately describe it?

### 4. Dependency changes

- Were any dependencies added? Are they pinned to exact versions? Are they justified?
- Were any dependencies removed? Is the manifest still consistent?

### 5. Security basics

- Does the change handle secrets, user input, network requests, or file operations?
- If so, were the secure-defaults rules followed? (No hardcoded secrets, parameterized queries, input validation)

### 6. Unrelated changes

- Does the diff contain anything not described in the plan?
- If so, either remove it or document why it's necessary.

### 7. Worktree discipline

- Was this a multi-file change? If so, was it done in a worktree (`.worktrees/<slug>/`)?
- If not, why not? (Trivial change is acceptable; "forgot" is not.)

### 8. Verification

- Does `kanon verify` pass (if the project uses kanon)?
- Do linters and type checkers pass?
- Is coverage at or above the configured floor?

### 9. Artifact status reconciliation

- For each artifact touched or completed by this work:
  - **Plans:** if all acceptance criteria are met, set `status: done`. If work has started but isn't complete, set `status: in-progress`.
  - **Specs:** if `fixtures_deferred` no longer applies (test files exist), replace it with `fixtures:` and `invariant_coverage:`.
  - **Design docs:** if the feature has shipped and the implementing spec is `status: accepted`, set the design doc to `status: accepted`.
- If any status field is stale, update it in this commit.

## Exit criteria

You have checked all 9 items and can state: "All acceptance criteria met. No test regressions. Docs updated. No unrelated changes. Artifact statuses current." If you cannot truthfully state this, the work is not done — identify what remains.

## Anti-patterns

- **"Looks done to me."** That's not a checklist pass. Each item needs specific evidence.
- **Skipping items because "they don't apply."** State why they don't apply rather than silently skipping.
- **Running the checklist after merging.** The checklist runs before declaring complete, not after.
