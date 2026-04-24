---
status: accepted
date: 2026-04-24
depth-min: 2
invoke-when: Implementing a plan or spec invariant at testing depth >= 2
---
# Protocol: AC-first + TDD

## Purpose

Translate plan acceptance criteria and spec invariants into executable tests before implementation begins. The agent iterates on implementation — not on weakening tests. A failing test is a signal that the implementation is wrong, not that the test is wrong.

## Steps

### 1. Read the plan's Acceptance Criteria

Open the plan being implemented. Find the `## Acceptance Criteria` (or `## Success Criteria`) section. List every criterion that can be expressed as an executable test.

### 2. Write failing tests for each testable AC item

For each criterion from step 1, write a test that encodes the expected behavior. Run the test suite — every new test should fail (red). If a test passes immediately, it's either trivially true or the behavior already exists.

### 3. Implement until AC tests pass

Write the minimum implementation that makes each failing test pass (green). Do not modify the tests to match the implementation — modify the implementation to match the tests.

### 4. TDD from spec invariants

When the task touches a spec invariant (`INV-*`), write a failing test for that invariant first. Implement until it passes. Refactor while keeping it green. Update the spec's `invariant_coverage:` frontmatter to reference the test.

### 5. Update invariant_coverage if applicable

If you wrote tests for spec invariants, add entries to the spec's frontmatter:

```yaml
invariant_coverage:
  INV-example-one:
    - tests/test_example.py::test_invariant_one
```

### 6. Escape hatches

Config changes, prose/documentation edits, and UI/template work that cannot be meaningfully unit-tested are exempt from test-first. Document how you verified these changes instead (e.g., "verified by manual inspection" or "verified by `kanon verify .`").

## Exit criteria

- Every testable AC item has a corresponding test.
- All AC tests pass.
- Spec invariant tests are referenced in `invariant_coverage:`.
- No test was weakened or deleted to make the suite pass.

## Anti-patterns

- **Writing tests after implementation.** Tests written after the fact tend to mirror the implementation rather than encode intended behavior.
- **Skipping AC items as "untestable."** If a criterion can't be tested, rewrite it — vague AC is a plan defect, not a testing problem.
- **Modifying tests to match broken implementation.** The implementation loop converges by adjusting code, not tests.
- **Ignoring `invariant_coverage:` updates.** Traceability is the payoff — don't skip the bookkeeping.
