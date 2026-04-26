---
status: accepted
date: 2026-04-24
depth-min: 1
invoke-when: Writing or modifying code
---
# Protocol: Test discipline

## Purpose

Ensure every code change is accompanied by tests that protect behavior. Agents follow these steps whenever they write or modify code, preventing silent test deletion, assertion weakening, and untested code from shipping.

## Steps

### 1. Identify what changed

Before committing, list every new function, modified behavior, or bug fix in the changeset.

### 2. Write or update tests

For each change identified in step 1, ensure a corresponding test exists. New functions get new tests. Modified behavior gets updated assertions. Bug fixes get regression tests that fail without the fix.

### 3. Verify no tests were deleted or weakened

Review the diff for removed test files, removed test functions, or weakened assertions (e.g., changing `assertEqual(x, 42)` to `assertTrue(x)`). If a test was removed, document what now covers the behavior it protected.

### 4. Check coverage

Run the project's coverage tool. Verify coverage is at or above the floor declared in `.kanon/config.yaml` (`aspects.testing.config.coverage_floor`, default 80%). If coverage dropped, add tests before proceeding.

### 5. Prefer test-first

When starting new work, write the test first. Watch it fail. Then implement. This shapes the implementation around verifiable behavior rather than retrofitting tests onto existing code.

## Exit criteria

- Every code change has a corresponding test.
- No tests were deleted without documented justification.
- No assertions were weakened without explaining why the old value was wrong.
- Coverage is at or above the configured floor.

## Anti-patterns

- **Deleting a failing test.** Fix the code or fix the test — never delete it.
- **`assert True` / `pass`-only tests.** A test that cannot fail protects nothing.
- **Testing mocks instead of behavior.** Tests should verify what the code does, not how it's wired.
- **Dropping coverage to ship faster.** Coverage debt compounds — maintain the floor.
