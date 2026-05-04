---
status: accepted
date: 2026-05-04
depth-min: 3
invoke-when: Writing or modifying tests at testing depth >= 3
---
# Protocol: Test Quality

## Purpose

Ensure tests verify behavior, not just structure. Supplements test-discipline (depth 1) and ac-first-tdd (depth 2) with quality checks that catch common LLM agent testing failures.

## Steps

### 1. Error-case coverage

For each tested function, write at least one error-case test alongside the happy-path test. Name it `test_<function>_error_<condition>` or `test_<function>_rejects_<input>`.

### 2. Public API only

Tests must call the public interface, not internal methods. Mock at boundaries (I/O, network, clock), never mock internal implementation details. If renaming a private method would break a test, the test is implementation-coupled.

### 3. Negative tests

Every feature test suite must include at least one negative test — verify that invalid input is rejected, not just that valid input is accepted.

### 4. Assertion specificity

Assertions must verify concrete values, not just existence. Prefer `assert result == expected` over `assert result is not None`. Prefer `assert "error" in message` over `assert message`.

## Exit criteria

- Each test suite has error-case and negative tests.
- No tests mock internal methods.
- Assertions check specific values.
