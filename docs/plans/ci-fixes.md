---
status: done
touches:
  - scripts/check_security_patterns.py
  - src/kanon/kit/aspects/kanon-security/files/scripts/check_security_patterns.py
  - scripts/check_test_quality.py
  - src/kanon/kit/aspects/kanon-testing/files/scripts/check_test_quality.py
  - .github/workflows/release.yml
---

# Plan: Fix CI scanner false positives and release workflow gap

## Tasks

- [x] T1: Add `# nosec` inline suppression to `check_security_patterns.py`.
  Lines containing `# nosec` are skipped. Update both copies (ci/ and
  kit aspect) to stay byte-identical.
- [x] T2: Restrict `check_test_quality.py` to scan only `tests/` and
  `test/` directories instead of rglob from root. Update both copies.
- [x] T3: Add the 9 missing CI script steps to `release.yml`'s verify
  job, mirroring `verify.yml`.

## Acceptance criteria

1. `check_security_patterns.py` reports zero false positives on the
   kanon repo (the 3 f-string warnings are suppressed with `# nosec`).
2. `check_test_quality.py` does not flag
   `src/kanon/_validators/test_import_check.py`.
3. `release.yml` runs the same CI scripts as `verify.yml`.
4. `scripts/check_kit_consistency.py` passes (byte-equality).
5. All existing tests pass.
