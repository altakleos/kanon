The `release` aspect is active with automation helpers. Follow the release checklist protocol before cutting any release.

- `ci/release-preflight.py` — validates version, changelog, tests, and lint before publish.
- `.github/workflows/release.yml` — reference CI workflow triggered by version tags.

<!-- kanon:begin:release/publishing-discipline -->
<!-- kanon:end:release/publishing-discipline -->
