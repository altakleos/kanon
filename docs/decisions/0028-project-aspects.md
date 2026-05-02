---
status: accepted
date: 2026-04-26
---
# ADR-0028: Project-defined aspects via prefixed source-namespacing

## Context

The aspect model (ADR-0012) defines aspects as the unit of opt-in discipline; the kit currently ships six (`sdd`, `worktrees`, `release`, `testing`, `security`, `deps`), all loaded from `src/kanon/kit/aspects/<name>/`. The model has no story for a consumer to declare its own aspects — a project that wants to encode platform-team-specific discipline (e.g., an `auth-policy` aspect with project-bespoke `validators:`) must either fork the kit or maintain a parallel mechanism outside the kit's reach.

The natural extension is composition: let consumers declare aspects in the same shape kit-aspects use, discovered from `.kanon/aspects/<name>/`, surfaced through the same `kanon aspect` CLI verbs, run by the same `kanon verify` orchestration. The hard sub-problem this surfaces is naming: a consumer-declared `testing` aspect would silently shadow the kit's `testing` aspect; a future kit rename of `testing` could collide with a consumer's existing one. ADR-0026's `provides:` capability registry insulates `requires:` predicates from rename brittleness, but the *aspect-name namespace itself* is unprotected.

A second, smaller sub-problem is the trust boundary for project-side `validators:` declarations — a consumer-authored aspect's `kanon verify` extension is, by construction, code that runs inside the kit's CLI process. The ADR has to ratify whether that's in-process (consistent with how the kit's own checks run) or sandboxed (more complex; smaller incremental cost over the existing trust the consumer already extends to the CLI).

A third concern is the migration discipline. Adopting source-namespacing means every existing consumer config and AGENTS.md marker that names a kit aspect needs to be rewritten to the prefixed form. The v0.1→v0.2 migration (ADR-0012) already established the one-way / idempotent / first-upgrade-applies pattern; this ADR commits to applying that pattern verbatim.

See [`docs/specs/project-aspects.md`](../specs/project-aspects.md) for the full invariant surface this ADR ratifies.

## Decision

Adopt **prefixed source-namespacing** as the aspect-name grammar, with two namespaces defined in this ADR and a third reserved for future use:

- `kanon-<local>` — declared by the kit, loaded from `src/kanon/kit/aspects/kanon-<local>/`.
- `project-<local>` — declared by the consumer, loaded from `.kanon/aspects/project-<local>/`.
- `acme-<local>` and any other namespaces — reserved by the grammar, not defined by this ADR (a future ADR would define third-party publishing).

### Bare-name sugar

At every input surface (CLI flags, `--aspects` parser, `aspect set-depth`/`set-config`/`add`/`remove` arguments, `requires:` depth predicates), an unprefixed name is sugar for the `kanon-` namespace. This preserves backward-compatibility for every existing CLI invocation. Project-aspect names have no shorthand — they must always be typed in their prefixed form. This is the single rule that resolves the ambiguity bare names would otherwise re-introduce.

### Discovery location

Project-aspects live at `.kanon/aspects/<project-name>/manifest.yaml` with the same per-aspect directory layout the kit uses. The CLI's `_load_aspect_registry(target)` unions kit-aspects (from the installed wheel) with project-aspects (from the consumer's tree) into a single in-memory registry every command operates on.

### Namespace ownership is source-bounded

A kit-side directory may only declare `kanon-` aspects; a project-side directory may only declare `project-` aspects. Crossing the boundary is a hard-fail at load time naming the offending path and the rule.

### Runtime ownership exclusivity

The cross-aspect file-path collision check (currently in `ci/check_kit_consistency.py`) lifts into `_build_bundle` runtime. The CI check remains as a kit-side belt-and-suspenders, but project-aspects can introduce collisions the CI cannot see, so the runtime guard is load-bearing.

### In-process validator trust boundary

A project-aspect's `validators:` field is a list of importable Python module paths. `kanon verify` imports each module and calls a known entrypoint — `def check(target: Path, errors: list[str], warnings: list[str]) -> None`. Findings flow into the same JSON report the kit's structural checks populate. Project-validator code runs with the same privileges as the CLI; the trust boundary is documented and not sandboxed. The ordering rule — kit structural checks run *after* project-validators — enforces non-overriding (a project-validator that calls `errors.clear()` finds its clear overwritten by the kit's subsequent appends).

### v2 → v3 config migration

A pre-namespace consumer config (v2: `aspects: {sdd: {...}}`) auto-migrates to v3 (`aspects: {kanon-sdd: {...}}`) on first `kanon upgrade` after this ADR's implementation lands. AGENTS.md marker prefixes (`<!-- kanon:begin:sdd/... -->` → `<!-- kanon:begin:kanon-sdd/... -->`) and `.kanon/protocols/<bare>/` → `kanon-<bare>/` directories migrate in the same operation. The migration is one-way, idempotent, and emits a single `Migrated v2 (bare) → v3 (namespaced) aspect names.` line. Older kanon CLIs reading a v3 config produce undefined behaviour — same migration discipline as v1 → v2 (ADR-0012).

## Alternatives Considered

1. **Hard-fail on collision; no namespace prefix.** A project-aspect with the same name as a kit-aspect refuses to load. Rejected: forces consumers to rename their project-aspect every time the kit adds an aspect with a colliding name. The kit should absorb that cost, not push it onto consumers. Namespace prefixing makes the collision impossible by construction.

2. **Auto-detection of source namespace from where the slug currently lives.** Bare names are looked up in both kit and project sources at load time. Rejected: the same input changes meaning when a project-aspect appears or disappears. Mapping bare names to `kanon-` exclusively makes resolution stable across every consumer's tree and across time.

3. **Different namespace separator: colon (`kanon:sdd`) or dot (`kanon.sdd`).** Both are common in other ecosystems. Rejected for hyphen on cosmetic and integration grounds: the kit's existing `_MARKER_RE` accepts `[a-z0-9/_-]+` for marker section names without modification; the colon would force a regex widening and produce three colons in a row in markers (`<!-- kanon:begin:kanon:sdd/foo -->`); the dot has no current usage but reads less naturally for a kebab-case ecosystem. The hyphen fits cleanly.

4. **Subprocess isolation for project-validators.** A project-validator runs in a separate Python interpreter, talking to the kit over JSON-on-stdio. Rejected: forces the kit's verify protocol (path argument, error/warning shape, JSON schema) over an IPC boundary; complicates exception propagation and stack traces; and the consumer already trusts the kit's CLI to run inside their working directory, so the in-process increment over the existing trust is small. A future spec may revisit if a real consumer demands sandboxing.

5. **Two parallel input grammars: bare for kit-aspects, prefixed for project-aspects.** Bare names continue to mean kit-aspects only; project-aspects must be prefixed. Recorded for the trail — this is the path adopted (the alternative was "prefixes optional on both sides," which collapses to alternative #2).

6. **Namespace prefixes on capabilities too.** `provides: [kanon-planning-discipline]`. Rejected: capabilities are an abstract substitutability namespace, not a source namespace; the whole point of ADR-0026 is to decouple the capability-name from the aspect that supplies it. Prefixing capabilities by source would re-couple them.

7. **Per-PR rename rather than big-bang Phase 1.** Rename one aspect at a time over multiple PRs. Rejected: the kit-side manifest, every aspect's `requires:` predicate, the AGENTS.md markers, the kit's own consumer state, and the CI checks all reference the aspect names; partial rename leaves the kit in an internally inconsistent state across PR boundaries. The plan keeps Phase 1 as one PR.

## Consequences

- **CLI surface is observably backward-compatible** for every existing kit-aspect invocation thanks to bare-name sugar. New project-aspect invocations are explicit (`kanon aspect add . project-auth-policy`); no shorthand.
- **`.kanon/config.yaml` schema bumps to v3.** Auto-migration from v2 (and transitively from v1 via the existing v1→v2 path) on first upgrade after this ADR's implementation lands. Older CLIs reading v3 configs produce undefined behaviour.
- **AGENTS.md marker grammar gains the `kanon-` prefix on every kit-section marker.** No regex changes — the existing `[a-z0-9/_-]+` character class already accommodates the hyphen.
- **`_check_cross_aspect_exclusivity` lifts from CI to runtime.** The CI variant stays for kit-internal hygiene; the runtime variant catches cross-source collisions the CI cannot see.
- **`_load_top_manifest` is superseded by `_load_aspect_registry(target)`** at every CLI command's entry point. Project-aspects participate in `aspect list`, `aspect info`, `aspect add`, `aspect set-depth`, `aspect set-config`, `aspect remove`, and `verify`.
- **Trust boundary for project-validators is in-process and documented.** Consumers who do not trust their own project-aspect's validator code should not declare it.
- **The kit's own consumer state (`.kanon/config.yaml`, `AGENTS.md`, `.kanon/protocols/`) migrates in Phase 1.** Self-hosting (P-self-hosted-bootstrap) requires the kit to apply the migration to itself before declaring the implementation complete.
- **Third-party aspect publishing (the `acme-` namespace) remains deferred** per ADR-0012 §Alternatives #5. This ADR reserves the namespace shape; a future ADR would define publishing.
- **Plan size.** Implementation is [`docs/plans/project-aspects.md`](../plans/archive/project-aspects.md) (PR #25): 36 tasks across 5 phases, intended to land as 5 sequential PRs.

## Config Impact

`.kanon/config.yaml` schema v3:

```yaml
kit_version: <semver>
aspects:
  kanon-<local>:
    depth: <int>
    enabled_at: <ISO-8601>
    config: {<aspect-specific>}
  project-<local>:
    depth: <int>
    enabled_at: <ISO-8601>
    config: {<aspect-specific>}
```

Auto-migration from v2 on first `kanon upgrade` after this ADR's implementation lands. Emits `Migrated v2 (bare) → v3 (namespaced) aspect names.` once.

## References

- [`docs/specs/project-aspects.md`](../specs/project-aspects.md) — invariants this ADR ratifies.
- [`docs/plans/project-aspects.md`](../plans/archive/project-aspects.md) — implementation plan.
- [ADR-0012](0012-aspect-model.md) — aspect model (the model this ADR extends).
- [ADR-0024](0024-crash-consistent-atomicity.md) — crash-consistent atomicity (the migration is wrapped in the existing sentinel discipline).
- [ADR-0026](0026-aspect-provides-and-generalised-requires.md) — `provides:` capability registry (insulates `requires:` from aspect-rename brittleness; this ADR's namespace grammar adds a complementary insulation at the aspect-identity layer).
- [ADR-0011](0011-kit-bundle-refactor.md) — kit-bundle refactor (manifest-driven membership; this ADR extends the manifest to a second source).
- [ADR-0007](0007-status-taxonomy.md) — status taxonomy (the spec is `draft` until Phase 5 promotes it to `accepted`; this ADR is `accepted` because the decision itself is final).
- `P-self-hosted-bootstrap`, `P-tiers-insulate`, `P-cross-link-dont-duplicate` — principles realised by composition.
