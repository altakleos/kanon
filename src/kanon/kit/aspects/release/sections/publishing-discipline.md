## Release Publishing Discipline

Every release follows a strict sequence: prepare, validate, tag, publish.

**Version bump:** Update `__version__` in `__init__.py` (or the project's canonical version source) and add a CHANGELOG entry for the new version before any other release step.

**Pre-release checks:** All of the following must pass before tagging:

- Full test suite (`pytest`)
- Lint (`ruff check`)
- `kanon verify .`

**Tag creation:** Create an annotated tag `vX.Y.Z` only after all checks pass. Never tag a dirty tree or a commit with failing checks.

**Publish gate:** CI workflow triggered by tag push handles build and publish. Manual `twine upload` or equivalent is a fallback, not the default.

**CHANGELOG is the source of truth** for release notes. Every user-visible change gets an entry before the release tag is created.

**Never publish without passing preflight checks.** A release that skips validation is a rollback waiting to happen.
