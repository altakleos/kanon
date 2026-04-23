# AGENTS.md — ${project_name}

A tier-3 `kanon` project. Full stack: foundations + specs + design + ADRs + plans + verification. All process gates are active.

## Boot chain

0. Read [`docs/foundations/vision.md`](docs/foundations/vision.md) — what the project is and is not.
1. Read [`docs/development-process.md`](docs/development-process.md) — the SDD method.
2. Read [`docs/decisions/README.md`](docs/decisions/README.md) — what has already been decided.
3. **Before editing any source file** for a non-trivial change, produce a plan and wait for approval — see § "Required: Plan Before Build" below.
4. **Before writing a design doc, ADR, plan, or implementation** for a new user-visible capability, produce a spec and wait for approval — see § "Required: Spec Before Design" below.

## Key Constraints

- Process rules belong in `docs/development-process.md`. README files in artifact directories carry indexes and templates, not process definitions.
- ADRs are immutable once accepted. To reverse one, write a superseding ADR.
- Principles in `docs/foundations/principles/` are the project's cross-cutting stances. Specs and ADRs reference them via frontmatter.

<!-- kanon:begin:plan-before-build -->
<!-- kanon:end:plan-before-build -->

<!-- kanon:begin:spec-before-design -->
<!-- kanon:end:spec-before-design -->

## Contribution Conventions

- **Commit messages** — prefer [Conventional Commits](https://www.conventionalcommits.org/) prefixes.
- **Changelog** — append every user-visible change to `## [Unreleased]` in `CHANGELOG.md` in the same commit.

## References

- [`docs/foundations/vision.md`](docs/foundations/vision.md) — product vision
- [`docs/foundations/principles/`](docs/foundations/principles/) — cross-cutting stances
- [`docs/development-process.md`](docs/development-process.md) — the SDD method
- [`docs/decisions/README.md`](docs/decisions/README.md) — ADR index
- [`docs/specs/README.md`](docs/specs/README.md) — spec index
- [`docs/design/README.md`](docs/design/README.md) — design doc index
- [`docs/plans/README.md`](docs/plans/README.md) — plan index
