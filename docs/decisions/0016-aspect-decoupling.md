---
status: accepted
date: 2026-04-24
---
# ADR-0016: Aspect decoupling — remove sdd as structurally privileged

## Context

The aspect model (ADR-0012) introduced aspects as opt-in discipline bundles. However, the implementation treats `sdd` as a structurally privileged god-aspect: it owns the AGENTS.md base template, `kanon init` hardcodes it, CI scripts hardcode its file paths, and the `${tier}` placeholder is an sdd alias. An audit found hardcoded `sdd` string literals in `cli.py` (4), `_scaffold.py` (12), and CI scripts (19). This coupling prevents adding new aspects without Python changes and makes sdd impossible to remove or replace.

## Decision

1. **Aspect-neutral AGENTS.md base.** Introduce `src/kanon/kit/agents-md-base.md` as the document skeleton. Aspects inject sections via markers; no aspect owns the skeleton.

2. **Generic init.** `kanon init` accepts `--aspects name:depth,...` with `--tier N` preserved as sugar. Default aspect set read from manifest `defaults:` key.

3. **`aspect add` / `aspect remove` commands.** `add` enables at default depth with `requires:` enforcement. `remove` deletes config entry and AGENTS.md markers, leaves files on disk.

4. **`requires:` enforcement.** Dependency predicates (`<aspect> <op> <depth>`) checked at runtime in `_set_aspect_depth`, `aspect add`, and `aspect remove`.

5. **Manifest-driven CI.** `check_package_contents.py` reads manifest for required paths. `check_kit_consistency.py` reads per-aspect `byte-equality:` sub-manifest key.

6. **Generic placeholders.** `${tier}` replaced with `${sdd_depth}`. Generic vocabulary: `${project_name}`, `${<aspect>_depth}`.

## Alternatives Considered

**Defer until a third aspect exists.** Rejected. More aspects are planned imminently. The coupling compounds — each new aspect would need to work around sdd's structural privilege. Decoupling at 2 aspects is cheaper than at 5.

**Partial decoupling (only fix init).** Rejected. The invariants are interdependent: generic init requires a base template; requires enforcement needs add/remove; manifest-driven CI needs the new keys. Partial fixes leave inconsistent states.

## Consequences

- `src/kanon/kit/agents-md-base.md` is a new file in the kit bundle.
- Top-level `manifest.yaml` gains a `defaults:` key.
- Per-aspect sub-manifests gain a `byte-equality:` key.
- `kanon init --aspects` is a new CLI flag.
- `kanon aspect add` and `kanon aspect remove` are new CLI commands.
- The `${tier}` placeholder is deprecated in favor of `${sdd_depth}` but preserved for backward compatibility.
- Legacy migration code (`format_version < 2`) may still reference `"sdd"` behind a version guard.

## References

- [Spec: Aspect decoupling](../specs/aspect-decoupling.md)
- [ADR-0012: Aspect model](0012-aspect-model.md)
- [Spec: Aspects](../specs/aspects.md)
