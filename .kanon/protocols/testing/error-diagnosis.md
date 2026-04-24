---
status: accepted
date: 2026-04-24
depth-min: 1
invoke-when: A test fails, a build breaks, or a command produces an unexpected error during implementation
---
# Protocol: Error-diagnosis

## Purpose

Diagnose failures systematically instead of making random changes until the error disappears. The test-discipline protocol says "don't weaken assertions" — this protocol tells the agent what to DO instead.

## Steps

### 1. Reproduce

Run the exact failing command. Capture the full output.

### 2. Read

Examine the complete error message or stack trace — not just the last line.

### 3. Hypothesize

State in one sentence what you believe is wrong and why.

### 4. Verify

Read the relevant source code to confirm your hypothesis before editing anything.

### 5. Fix the root cause

Fix the root cause, not the symptom. If the fix is in test code, explain why the test was wrong (not the implementation).

### 6. Re-run the full test suite

Not just the previously-failing test. A fix that breaks something else is not a fix.

### 7. Step back if stuck

If the same error persists after 2 fix attempts, step back. Re-read the error from scratch. Consider whether your mental model of the code is wrong.

## Exit criteria

The original error is resolved, the full test suite passes, and no assertions were weakened.

## Anti-patterns

- **Changing the assertion to match the (wrong) output.** Fix the code, not the test.
- **Deleting the failing test.** That's destroying evidence, not fixing the problem.
- **Making random changes hoping something works.** Each change must be justified by a hypothesis.
- **Fixing only the failing test without running the full suite.** Regressions hide in passing tests.
