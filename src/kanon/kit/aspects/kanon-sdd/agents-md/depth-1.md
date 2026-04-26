A `kanon` project with `sdd` at depth 1. The plan-before-build gate is active; ADRs and plans are tracked under `docs/`.

## Boot chain

0. Read this file.
1. Read [`docs/development-process.md`](docs/development-process.md) — the SDD method.
2. Read [`docs/decisions/README.md`](docs/decisions/README.md) — what has already been decided.
3. **Before editing any source file** for a non-trivial change, produce a plan and wait for approval — see § "Required: Plan Before Build" below.

## Key Constraints

- Process rules belong in `docs/development-process.md`. README files in artifact directories carry indexes and templates, not process definitions.
- ADRs are immutable once accepted. To reverse one, write a superseding ADR.

## References

- [`docs/development-process.md`](docs/development-process.md) — the SDD method
- [`docs/decisions/README.md`](docs/decisions/README.md) — ADR index
- [`docs/plans/README.md`](docs/plans/README.md) — plan index + template
