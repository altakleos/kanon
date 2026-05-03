---
status: accepted
date: 2026-05-01
implements: docs/specs/dialect-grammar.md
---
# Design: Dialect grammar — concrete schemas, composition algorithm, and the validator

## Context

[`docs/specs/dialect-grammar.md`](../specs/dialect-grammar.md) defines *what* the substrate's contract grammar IS and what invariants the kernel enforces. This design specifies *how* the kernel implements those invariants: the concrete `realization-shape:` schema, the dialect frontmatter shape, the composition resolution algorithm, the `kanon contracts validate` walk, and the Phase A footprint.

[ADR-0041](../decisions/0041-realization-shape-dialect-grammar.md) is the parent ratification.

## Realization-shape: concrete schema

A contract's frontmatter declares `realization-shape:` per [ADR-0041 Decision §1](../decisions/0041-realization-shape-dialect-grammar.md):

```yaml
# A preflight.commit contract (e.g., kanon-testing/preflight)
---
contract-id: kanon-testing/preflight
semantic-version: 1.0
surface: preflight.commit
before: []
after: []
realization-shape:
  verbs: [lint, test, typecheck, format]
  evidence-kinds: [config-file, ci-workflow, build-script]
  stages: [commit, push, release]
  additional-properties: false
provides:
  - test-discipline
---
```

```yaml
# A release-gate contract (e.g., kanon-release/release-gate)
---
contract-id: kanon-release/release-gate
semantic-version: 1.0
surface: release-gate.tag
before: []
after: [kanon-testing/preflight]
realization-shape:
  verbs: [scan, audit, sign, publish]
  evidence-kinds: [ci-workflow, release-config, signing-key-reference]
  stages: []
  additional-properties: false
provides:
  - release-discipline
---
```

### Field semantics

- **`verbs:`** — A YAML list of strings, each from the substrate's enumerated verb set. The substrate's v1 dialect (`2026-05-01`) declares the canonical verb enumeration; future dialects may extend. Resolutions citing verbs not in the contract's declared set are rejected.
- **`evidence-kinds:`** — A YAML list of strings naming evidence categories the agent may cite. Helps the agent narrow its search; helps the validator detect "the agent cited a CI workflow as evidence for a contract that explicitly excluded `ci-workflow`."
- **`stages:`** — A list of stage names this contract orders against. Empty for non-staged contracts (release-gates, security-reviews). Non-empty for preflight contracts: each invocation in the resolution lives in exactly one stage.
- **`additional-properties:`** — Boolean. Default `false`. When `false`, resolution entries with keys outside the declared shape are rejected. When `true`, extra keys pass through (forward-compatibility hatch a publisher explicitly opts into).

### The substrate's v1 dialect verb enumeration

```yaml
# v1 dialect (kanon-dialect: 2026-05-01) verb enumeration
verbs:
  - lint           # static-analysis checks
  - test           # automated test execution
  - typecheck      # static type validation
  - format         # code formatting verification
  - scan           # security or dependency scanning
  - audit          # compliance or licensing audit
  - sign           # cryptographic signing
  - publish        # release / deploy
  - report         # informational output
```

A future dialect may extend this enumeration; the v1 set is intentionally narrow.

## Dialect frontmatter

Every aspect manifest declares the dialect at the top level:

```yaml
# kanon-aspects/aspects/kanon_testing/manifest.yaml
kanon-dialect: 2026-05-01
publisher: kanon-aspects
aspect-id: kanon-testing
# ... rest of aspect manifest ...
```

The substrate ships a list of supported dialects in its source. v0.4's substrate ships `[2026-05-01]`. A future v0.5 may ship `[2026-05-01, 2026-09-01]` (honouring N-1 per [INV-dialect-grammar-version-format](../specs/dialect-grammar.md)).

### Substrate-side dialect registry

```python
# Conceptual: src/kanon/_dialects.py (Phase A)
SUPPORTED_DIALECTS = ["2026-05-01"]
DEPRECATION_WARNING_BEFORE = ["2026-05-01"]  # nothing deprecated yet

def validate_dialect_pin(manifest_dialect: str) -> None:
    if manifest_dialect not in SUPPORTED_DIALECTS:
        raise UnknownDialectError(
            f"manifest pins kanon-dialect: '{manifest_dialect}' "
            f"but substrate supports {SUPPORTED_DIALECTS}"
        )
    if manifest_dialect in DEPRECATION_WARNING_BEFORE:
        warnings.warn(
            f"kanon-dialect: '{manifest_dialect}' is deprecated; "
            f"migrate to {SUPPORTED_DIALECTS[-1]} before next dialect supersession"
        )
```

## Composition resolution algorithm

When multiple contracts target the same `surface:`, the kernel orders them via topological sort over `before:` / `after:` edges. Pseudocode:

```python
def compose_contracts(contracts: list[Contract], surface: str) -> list[Contract]:
    # Step 1: filter to contracts targeting this surface
    candidates = [c for c in contracts if c.surface == surface]

    # Step 2: resolve replaces: substitution
    replacements = {}  # replaced_id -> replacing_contract
    for c in candidates:
        for replaces_target in c.replaces:
            if replaces_target.matches_loaded(candidates):
                replacements[replaces_target.contract_id] = c
    # Drop replaced contracts; replacing contracts inherit provides:
    active = []
    for c in candidates:
        if c.contract_id in replacements:
            continue  # this one is replaced
        active.append(c)

    # Step 3: build directed graph
    graph = {c.contract_id: set() for c in active}
    for c in active:
        for before_target in c.before:
            graph[c.contract_id].add(before_target)  # c executes before target
        for after_target in c.after:
            graph[after_target].add(c.contract_id)  # target executes before c

    # Step 4: topological sort
    try:
        ordering = topological_sort(graph)
    except CycleError as e:
        raise CompositionCycleError(
            f"Composition cycle on surface '{surface}': {e.cycle_path}"
        )

    # Step 5: return contracts in topological order
    return [active_by_id[cid] for cid in ordering]
```

### Cycle reporting

When a cycle exists, the error names every contract in the cycle and the `before/after:` edge declaring it:

```
ERROR: composition cycle on surface 'preflight.commit':
  kanon-testing/preflight  --before-->  acme-strict-testing/preflight
  acme-strict-testing/preflight  --before-->  kanon-testing/preflight

Resolution: review the `before:` and `after:` declarations in the
two contracts and remove the conflicting edge. Cycles in composition
graphs are publisher bugs; the substrate refuses to load them.
```

### Ambiguity (no relationship between same-surface contracts)

If two contracts target the same surface and have no `before/after:` relationship, the topo-sort produces a non-deterministic ordering. The substrate detects this case at load time and emits `code: ambiguous-composition` as a *warning* (not error) — the kernel proceeds with a stable but unspecified order (typically alphabetical by contract-id) but informs the consumer their composition is under-specified. Future ADRs may add `prefer:` directives for explicit resolution; v0.4 surfaces the ambiguity and lets the consumer review.

## The `kanon contracts validate <bundle-path>` walk

A publisher-facing CLI verb (Phase A) that pre-flights a bundle before publishing. Algorithm:

```python
def validate_bundle(bundle_path: Path) -> ValidationReport:
    report = ValidationReport()
    manifest_path = bundle_path / "manifest.yaml"
    if not manifest_path.exists():
        report.error("missing-manifest", f"no manifest.yaml at {bundle_path}")
        return report

    manifest = load_yaml(manifest_path)

    # 1. Dialect pin
    if "kanon-dialect" not in manifest:
        report.error("missing-dialect-pin", "manifest must pin kanon-dialect:")
    elif manifest["kanon-dialect"] not in SUPPORTED_DIALECTS:
        report.error("unknown-dialect", f"unsupported: {manifest['kanon-dialect']}")

    # 2. Per-contract realization-shape
    for contract in manifest.get("contracts", []):
        if "realization-shape" not in contract:
            report.error("missing-realization-shape", contract["contract-id"])
            continue
        validate_shape_against_dialect(contract["realization-shape"], manifest["kanon-dialect"], report)

    # 3. Composition pre-flight: build graph, detect cycles, without executing
    by_surface = group_by_surface(manifest.get("contracts", []))
    for surface, candidates in by_surface.items():
        try:
            compose_contracts(candidates, surface)
        except CompositionCycleError as e:
            report.error("composition-cycle", str(e))

    # 4. replaces: target validation
    for contract in manifest.get("contracts", []):
        for replaces in contract.get("replaces", []):
            # Note: a publisher's bundle may legitimately replace a contract
            # not in this bundle. The validator does not error on missing targets;
            # it only errors on within-bundle replacement cycles.
            pass  # handled in compose_contracts step

    return report
```

### Output shape

```json
{
  "bundle": "/path/to/acme-fintech-compliance",
  "dialect": "2026-05-01",
  "contracts": ["acme-fintech-compliance/audit-review"],
  "errors": [],
  "warnings": [],
  "status": "ok"
}
```

The verb is a publisher's go/no-go signal before pushing a release; CI configurations for `acme-` publishers are expected to wire it into their build pipelines.

## Phase A implementation footprint

| Surface | LOC delta | What |
|---|---:|---|
| `_dialects.py` (new) | ~+60 | Supported-dialect registry, validation function |
| `_realization_shape.py` (new) | ~+120 | Shape parser, resolution-against-shape validator |
| `_composition.py` (new) | ~+150 | Topo-sort, cycle detection, replaces resolution |
| `_manifest.py` extensions | ~+40 | Dialect-pin validation at load time |
| `_resolutions.py` extensions | ~+50 | Shape-validation in replay path |
| `cli.py: kanon contracts validate` | ~+80 | New verb |
| Migration: existing kit-side manifests | ~+50 | Add `kanon-dialect: 2026-05-01` to every shipped manifest; add `realization-shape:` to every shipped contract |
| Tests | ~+250 | ~30 cases across the six INVs |

Total: ~+800 LOC source / +250 LOC tests across ~15 files.

## Decisions

- [ADR-0041](../decisions/0041-realization-shape-dialect-grammar.md) — parent decision for this design.
- [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment.
- [ADR-0039](../decisions/0039-contract-resolution-model.md) — runtime-binding model; shape-validation slots into the replay path.
- [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) — discovery interface; dialect-pin is checked at entry-point load.
- [ADR-0026](../decisions/0026-aspect-provides-and-generalised-requires.md) — capability registry; `replaces:` preserves inheritance.
