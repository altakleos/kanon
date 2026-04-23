# AGENTS.md — ${project_name}

A tier-2 `kanon` project. Plan-before-build and spec-before-design gates are both active; specs are tracked under `docs/specs/`.

## Boot chain

0. Read this file.
1. Read [`docs/development-process.md`](docs/development-process.md) — the SDD method.
2. Read [`docs/decisions/README.md`](docs/decisions/README.md) — what has already been decided.
3. **Before editing any source file** for a non-trivial change, produce a plan and wait for approval — see § "Required: Plan Before Build" below.
4. **Before writing a design doc, ADR, plan, or implementation** for a new user-visible capability, produce a spec and wait for approval — see § "Required: Spec Before Design" below.

## Key Constraints

- Process rules belong in `docs/development-process.md`. README files in artifact directories carry indexes and templates, not process definitions.
- ADRs are immutable once accepted. To reverse one, write a superseding ADR.

<!-- kanon:begin:plan-before-build -->
<!-- kanon:end:plan-before-build -->

<!-- kanon:begin:spec-before-design -->
<!-- kanon:end:spec-before-design -->

<!-- kanon:begin:protocols-index -->
<!-- kanon:end:protocols-index -->

## Contribution Conventions

- **Commit messages** — prefer [Conventional Commits](https://www.conventionalcommits.org/) prefixes.
- **Changelog** — append every user-visible change to `## [Unreleased]` in `CHANGELOG.md` in the same commit.

## References

- [`docs/development-process.md`](docs/development-process.md) — the SDD method
- [`docs/decisions/README.md`](docs/decisions/README.md) — ADR index
- [`docs/specs/README.md`](docs/specs/README.md) — spec index + template
- [`docs/plans/README.md`](docs/plans/README.md) — plan index + template
