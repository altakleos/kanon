The `testing` aspect is active with automated enforcement. Follow the test-discipline and ac-first-tdd protocols when writing or modifying code.

- At depth 2+: translate plan acceptance criteria into failing tests before implementation.
- For spec invariants: red-green-refactor loop.
- `ci/check_test_quality.py` — validates test quality (no empty tests, no assert-True-only, coverage floor).

