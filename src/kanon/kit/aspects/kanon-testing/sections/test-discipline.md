## Test Discipline

Tests exist to protect behavior, not to produce a green badge. Every code change follows these rules:

**Tests accompany code changes.** Every new function, behavior change, or bug fix gets a test in the same commit or adjacent commit. No untested code ships.

**Tests are not deleted without justification.** When removing a test, document what now covers the behavior it protected, or acknowledge the coverage gap. Never delete a test solely because it's failing — fix the code or fix the test.

**Assertions are not weakened to make tests pass.** Changing an expected value requires explaining why the old value was wrong. If the test is failing, the implementation is wrong — not the test.

**Prefer test-first.** Before implementing, consider "how will I verify this works?" and let that shape the implementation. Write the test, watch it fail, then implement.

**Maintain coverage at or above the configured floor.** The coverage floor is declared in `.kanon/config.yaml` under `aspects.testing.config.coverage_floor` (default 80%). The kit declares this value as advisory metadata; consumers wire it into their own CI pipeline (e.g., `pytest --cov-fail-under=$VALUE` or the equivalent in another language's tooling). The kit does not auto-wire the configured value into a test runner. Do not merge changes that drop coverage below the project's threshold.

**At depth 2+: AC-first testing.** Translate plan acceptance criteria into failing tests before implementation. For spec invariants, follow the red-green-refactor loop. See the `ac-first-tdd` protocol.
