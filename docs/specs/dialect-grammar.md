---
status: accepted
date: 2026-05-01
design: "docs/design/dialect-grammar.md"
realizes:
  - P-prose-is-code
  - P-publisher-symmetry
  - P-protocol-not-product
  - P-specs-are-source
stressed_by:
  - acme-publisher
  - solo-with-agents
fixtures_deferred: "Phase A authors the dialect parser, shape validator, composition resolver, and `kanon contracts validate` CLI verb. The dialect-grammar invariants below are the contract; tests land in the implementation PR."
---
# Spec: Dialect grammar — realization-shape, dialect versioning, and composition algebra

## Intent

Define the substrate's contract grammar — the shape every aspect manifest and contract must conform to, the date-stamped dialect-versioning that makes grammar evolution safe across publishers, and the composition algebra that determines execution ordering when multiple contracts target the same surface.

Per [ADR-0041](../decisions/0041-realization-shape-dialect-grammar.md), three commitments converge in this grammar: realization-shape per contract; dialect-version pinning; composition algebra (`surface:` + `before/after:` + `replaces:`). Together they make the substrate's "publishers can author against stable guarantees" promise concrete.

## Invariants

<!-- INV-dialect-grammar-pin-required -->
1. **Dialect pin required.** Every aspect manifest declares `kanon-dialect: YYYY-MM-DD` at the top level. Manifests without a dialect-pin fail at load time with `code: missing-dialect-pin`.

<!-- INV-dialect-grammar-version-format -->
2. **Dialect version is date-stamped.** The pin format is `YYYY-MM-DD`. The substrate honours at least the current dialect (N) and the previous dialect (N-1); manifests pinning N-2 or older receive a deprecation warning but still load. Manifests pinning a dialect newer than the substrate knows fail at load with `code: unknown-dialect`.

<!-- INV-dialect-grammar-realization-shape-required -->
3. **Realization-shape required per contract.** Every contract authored against the substrate's grammar declares a `realization-shape:` frontmatter block specifying allowed verbs, evidence kinds, and (where applicable) stage keys. Contracts without `realization-shape:` are rejected with `code: missing-realization-shape`.

<!-- INV-dialect-grammar-shape-validates-resolutions -->
4. **Kernel validates resolutions against shape.** At replay time, the kernel checks every resolution entry against its contract's `realization-shape:`: declared verbs match the entry's invocations; declared evidence kinds match the cited evidence; stage keys (when present) match the entry's stage. Mismatches are `code: shape-violation` findings, never silent.

<!-- INV-dialect-grammar-composition-acyclic -->
5. **Composition graph MUST be acyclic.** When multiple contracts target the same `surface:` and declare `before:` / `after:` ordering, the kernel topologically sorts. Cycles fail at load time with `code: composition-cycle` and an explicit cycle-path report (the sequence of contracts forming the cycle, with their `before/after:` edges named).

<!-- INV-dialect-grammar-replaces-substitution -->
6. **`replaces:` resolves before composition.** A contract declaring `replaces: <contract-id>@<version-range>` substitutes for the named contract at the version range. Resolution: the replacing contract inherits the replaced contract's `provides:` capability declarations (per [ADR-0026](../decisions/0026-aspect-provides-and-generalised-requires.md)); the replaced contract drops out of subsequent composition. A `replaces:` declaration that names a non-loaded contract is a no-op (no error); naming an enabled contract that is itself replaced is a `code: replacement-cycle` error.

## Rationale

These six invariants enforce the protocol-substrate's three commitments in code paths that the kernel can mechanically check.

- **Invariants 1 and 2** make grammar evolution safe: every publisher pins, the substrate honours an explicit window, supersession is calendar-driven (a dialect ADR is a real artifact, not an implicit kernel-version bump).
- **Invariants 3 and 4** make resolutions auditable: the agent's output has a typed target; the kernel rejects nonsense; reviewers can read a shape and know what fields a resolution will have.
- **Invariants 5 and 6** make composition deterministic: publishers declare ordering explicitly; the substrate fails loudly on contradiction; multi-publisher composition has well-defined semantics.

The grammar is deliberately minimal — six invariants, no further frontmatter — to leave maximum room for `acme-` publishers to author within. Future ADRs may extend (e.g., dialect-versioned realization-shape evolution); for v0.4, this is the foundation.

## Out of Scope

- **Specific realization-shapes for the seven `kanon-` reference contracts.** These are publisher artifacts (in `kanon-aspects`); they conform to the grammar specified here but are not part of the grammar.
- **Cross-publisher recipe import grammar.** Recipes (publisher-shipped target-tree YAML opting consumers into multiple contracts) are ratified by ADR-0043 (distribution + cadence).
- **Mechanical migration translators between dialects.** Round-2 panel raised this as a longevity concern; the substrate's commitment is to ratify a future ADR with mechanical translators when a dialect supersession requires it. v0.4 ships one dialect; the translator question lives in the future.
- **Consumer-side `prefer:` directives** for resolving ambiguous composition. Future ADR territory.
- **Realization-shape constraints on `provides:` / `requires:` capability lists.** Capabilities are governed by ADR-0026's grammar; this spec does not extend them.
- **Semantic correctness of resolutions against the contract's intent** — outside the kernel's mechanical verification boundary (per the verification-contract spec's INV-11).

## Structured error codes — normative emitter map

The six invariants above promise specific structured `code:` values. The substrate's runtime emits them from these symbols (kept in lockstep with the spec via the parity tests in `tests/test_dialects.py`, `tests/test_realization_shape.py`, `tests/test_composition.py`):

| Spec code | Emitted by | Surface (consumer-facing) |
|---|---|---|
| `missing-dialect-pin` | `kanon._dialects.DialectPinError` (raised by `validate_dialect_pin` when pin is `None`/empty) | substrate startup error; `kanon contracts validate` JSON `errors[].code` |
| `unknown-dialect` | `kanon._dialects.DialectPinError` (raised by `validate_dialect_pin` when pin not in `SUPPORTED_DIALECTS`) | substrate startup error; `kanon contracts validate` JSON `errors[].code` |
| `missing-realization-shape` | `kanon.cli.contracts_validate` (when a contract entry has no `realization-shape:` key) | `kanon contracts validate` JSON `errors[].code` |
| `invalid-realization-shape` | `kanon._realization_shape.ShapeParseError` (raised by `parse_realization_shape` for malformed shape, unsupported dialect, or verbs outside the dialect's enumeration) | `kanon contracts validate` JSON `errors[].code`; `kanon._resolutions.ReplayError.code` from `_validate_shape_against_contract` |
| `shape-violation` | `kanon._realization_shape.ShapeValidationError.code` (default; emitted by `validate_resolution_against_shape` for every mismatch — diagnostic kind in `subcode:` ∈ `{invalid-verb, invalid-evidence-kind, invalid-stage, unknown-key}`) | `kanon._resolutions.ReplayError.code` from `_validate_shape_against_contract`; subcode prepended to `reason` |
| `composition-cycle` | `kanon._composition.CompositionError.code` (raised by `compose` when `before:`/`after:` declarations form a directed cycle) | `kanon contracts validate` JSON `errors[].code` |
| `replacement-cycle` | `kanon._composition.CompositionError.code` (raised by `compose` when `replaces:` declarations form a cycle — distinct from `composition-cycle` per INV 6) | `kanon contracts validate` JSON `errors[].code` |
| `ambiguous-composition` | `kanon._composition.CompositionError.code` (warning; emitted by `compose` when two contracts on the same `surface:` declare no `before/after:` ordering between them) | `kanon contracts validate` JSON `warnings[].code` |

The `kanon._dialects.DialectPinError` and `kanon._realization_shape.ShapeParseError` exception classes both subclass `click.ClickException` so existing `except click.ClickException` callers continue to catch them; the spec-aligned `code` attribute is read by callers that emit structured JSON. `kanon._resolutions.ReplayError` carries the spec-aligned `code` directly (for `shape-violation` findings) and prepends the diagnostic `subcode` into `reason` for tooling that wants the finer kind.

## Decisions

- [ADR-0041](../decisions/0041-realization-shape-dialect-grammar.md) — realization-shape, dialect grammar, composition algebra (this spec's parent decision).
- [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (the why).
- [ADR-0039](../decisions/0039-contract-resolution-model.md) — resolution model; this grammar is what resolutions validate against.
- [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) — discovery interface; dialect pin is checked at the entry-point load step.
- [ADR-0026](../decisions/0026-aspect-provides-and-generalised-requires.md) — capability registry; `replaces:` substitution preserves capability inheritance per this ADR.
