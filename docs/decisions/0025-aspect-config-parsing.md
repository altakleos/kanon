---
status: accepted (lite)
date: 2026-04-25
weight: lite
---
# ADR-0025: Aspect-config CLI parsing — YAML scalar + optional schema

## Decision

`kanon aspect set-config <target> <name> <key>=<value>` and `kanon aspect add --config <key>=<value>` parse the value half via `yaml.safe_load`. Lists and mappings are rejected. Each aspect may optionally declare a `config-schema:` block in its sub-manifest at `src/kanon/kit/aspects/<name>/manifest.yaml`; when present, the CLI rejects unknown keys and type mismatches.

## Why

The `testing` aspect already stores `coverage_floor: 80` as an integer in consumer configs. If the CLI stored the string `"80"` instead, downstream config-aware code would either break or grow a parallel string-handling path. YAML-scalar parsing makes the CLI's storage match what an author would have hand-written into `.kanon/config.yaml`. Optional-but-validated schema lets experimental aspects ship without committing to a schema while still allowing stable aspects to catch typos and type mistakes at the CLI boundary.

## Alternative

Always store values as opaque strings and let each aspect interpret. Rejected: it pushes parsing into every consumer of the config block and creates silent drift between the CLI's storage and the aspect-author's mental model. Mandating a schema for every aspect was also rejected: it would block experimental aspects from shipping without one and inflate the ceremony required to add a new aspect.

## References

- [`docs/specs/aspect-config.md`](../specs/aspect-config.md) — the contract.
- [ADR-0012](0012-aspect-model.md) — advertised the surface; this ADR retroactively makes that ADR honest.
- [ADR-0024](0024-crash-consistent-atomicity.md) — atomic write contract that `set-config` participates in.
