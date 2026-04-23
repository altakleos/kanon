---
status: accepted
date: 2026-04-22
---
# ADR-0001: Distribution as pip package

## Context

`kanon` needs a distribution mechanism that lets a consumer project adopt the kit with one command, stays upgradeable over time, and doesn't pin the kit to a specific language ecosystem. The kit itself is Python (for the CLI), but its *output* — the scaffolded bundle — is language-agnostic prose + YAML that any project in any language can consume.

## Decision

Distribute the kit as a pip package named `kanon`, installable via `pipx install kanon` (or `pip install kanon` inside a venv). The CLI entry point `kanon` exposes `init`, `upgrade`, `verify`, `tier`, and `--version`. The kit's scaffolded templates are vendored as data files under `src/kanon/templates/` inside the wheel, copied onto target repos by the CLI.

Kit version is recorded in the consumer repo at `.kanon/config.yaml` (field: `kit_version`). The CLI refuses to upgrade a consumer instance if the installed package is older than the recorded version, and emits a clear message when a newer version is available.

## Alternatives Considered

1. **GitHub template repo.** Forks of the template diverge instantly — no upgrade path. Rejected.
2. **curl-install script** (`curl … | bash`). No provenance, no version pinning, broken the first time the URL moves. Rejected.
3. **npm package.** Ties non-JS projects to Node tooling they don't use. Alienates Python/Go/Rust consumer repos. Rejected.
4. **Homebrew formula.** macOS-only; secondary to pip for coverage. Not rejected, just out of scope for v0.1.
5. **Pip package** (chosen). Python is installed on essentially every developer box; pipx isolates the kit; the wheel's data-directory pattern (used by Sensei at `src/sensei/engine/`) handles the template-vendoring cleanly.

## Consequences

- Consumer repos don't need to be Python projects — the kit only needs Python at adoption time (and at upgrade time).
- CI for `kanon` ships the wheel-contents validator (`ci/check_package_contents.py`) to prevent consumer-state files from leaking into the package.
- Versioning follows PEP 440; alpha releases are marked `v0.1.0a1`-style.
- New harnesses added to `harnesses.yaml` (a vendored data file) don't require a new Python release — but shim generation still reads the registry at `init` time, so consumers on an old kit version miss new harness support until they upgrade. This is acceptable; `upgrade` is a cheap command.

## Config Impact

None beyond the `.kanon/config.yaml` file in consumer repos.

## References

- Sensei's ADR-0004 (distribution model) for prior art on vendored data directories + pip.
