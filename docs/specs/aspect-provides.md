---
status: accepted
date: 2026-04-25
realizes:
  - P-prose-is-code
serves:
  - vision
fixtures:
  - tests/test_aspect_provides.py
invariant_coverage:
  INV-aspect-provides-provides-field:
    - tests/test_aspect_provides.py::test_provides_field_round_trips
    - tests/test_aspect_provides.py::test_provides_empty_list_is_valid
    - tests/test_aspect_provides.py::test_provides_non_list_rejected
    - tests/test_aspect_provides.py::test_provides_invalid_capability_name_rejected
  INV-aspect-provides-requires-generalised:
    - tests/test_aspect_provides.py::test_classify_depth_predicate_three_tokens
    - tests/test_aspect_provides.py::test_classify_capability_one_token
    - tests/test_aspect_provides.py::test_classify_rejects_two_tokens
    - tests/test_aspect_provides.py::test_classify_rejects_four_tokens
    - tests/test_aspect_provides.py::test_classify_rejects_unknown_operator
    - tests/test_aspect_provides.py::test_classify_rejects_non_integer_depth
    - tests/test_aspect_provides.py::test_check_requires_mixed_depth_and_capability
  INV-aspect-provides-capability-name-format:
    - tests/test_aspect_provides.py::test_classify_rejects_uppercase_capability
    - tests/test_aspect_provides.py::test_provides_invalid_capability_name_rejected
  INV-aspect-provides-resolution:
    - tests/test_aspect_provides.py::test_check_requires_capability_satisfied
    - tests/test_aspect_provides.py::test_check_requires_capability_unsatisfied
    - tests/test_aspect_provides.py::test_check_requires_capability_unsatisfied_when_supplier_at_depth_zero
    - tests/test_aspect_provides.py::test_check_requires_depth_predicate_unchanged
  INV-aspect-provides-removal-check:
    - tests/test_aspect_provides.py::test_removal_blocked_by_depth_dependent
    - tests/test_aspect_provides.py::test_removal_blocked_when_only_supplier_being_removed
    - tests/test_aspect_provides.py::test_removal_allowed_when_alternative_supplier_remains
  INV-aspect-provides-info-surfaces:
    - tests/test_aspect_provides.py::test_aspect_info_surfaces_provides_for_sdd
    - tests/test_aspect_provides.py::test_aspect_info_provides_none_when_aspect_has_no_provides
  INV-aspect-provides-ci-validates-completeness:
    - tests/test_aspect_provides.py::test_ci_check_requires_resolution_passes_on_live_kit
    - tests/test_aspect_provides.py::test_ci_check_requires_resolution_flags_dangling_capability
  INV-aspect-provides-multiple-suppliers:
    - tests/test_aspect_provides.py::test_multiple_suppliers_recognised
    - tests/test_aspect_provides.py::test_removal_allowed_when_alternative_supplier_remains
  INV-aspect-provides-all-aspects-declare:
    - tests/test_aspect_provides.py::test_every_shipped_aspect_declares_capability
    - tests/test_aspect_provides.py::test_kit_manifest_yaml_matches_loader
  INV-aspect-provides-no-silent-meaning-change:
    - tests/test_aspect_provides.py::test_existing_kit_requires_predicates_classify_as_depth
    - tests/test_aspect_provides.py::test_check_requires_depth_predicate_unchanged
---
# Spec: Aspect capability namespace (`provides:`)

## Intent

Today, the only way one aspect can depend on another is by name and depth, via a `requires:` predicate like `"sdd >= 1"`. That coupling is fragile in two ways:

1. **Renaming an aspect breaks every dependent silently** — a future rename of `sdd` to (say) `methodology` would silently change the meaning of every `"sdd >= 1"` predicate in every consumer's `.kanon/config.yaml`. There is no abstraction to mediate.
2. **There is no way to express "I need feature X" without naming the aspect that supplies it.** Two different aspects might both legitimately supply the same capability (e.g., a future `lean-sdd` providing the same planning-discipline as `sdd`); today, dependents must name one or the other.

This spec adds a capability namespace that decouples *what* an aspect provides from *which* aspect supplies it:

- A new optional **`provides:`** field on each top-level aspect entry — a list of capability names.
- The existing `requires:` field is **generalised** to accept two predicate forms in the same list:
    - **Depth predicate** (3 whitespace-separated tokens): `"sdd >= 1"` — checked against the aspect's enabled depth, exactly as today.
    - **Capability presence** (1 token, matching the capability regex): `"planning-discipline"` — satisfied iff at least one enabled aspect declares that capability in its `provides:`.
- Resolution at `kanon init` / `aspect add` / `aspect set-depth` time evaluates every entry in `requires:` against the proposed aspect-set.

This is the v1 of a capability registry. The audit risk-register flagged it as cheap to introduce *now* and impossible after v1.0.

## Invariants

<!-- INV-aspect-provides-provides-field -->
1. **`provides:` field.** Each top-level aspect entry in `src/kanon/kit/manifest.yaml` may declare `provides: [<capability>, ...]`. The field is optional — aspects with no declared capabilities omit it entirely. When present, it is a YAML list of capability names; an empty list (`provides: []`) is valid and equivalent to absence.

<!-- INV-aspect-provides-requires-generalised -->
2. **`requires:` accepts two predicate forms.** Each entry in `requires:` is parsed as:
    - **Depth predicate** when whitespace-tokenisation produces three tokens (`<aspect-name> <op> <depth>`). Operators: `>=`, `>`, `==`, `<=`, `<`. Semantics unchanged from today.
    - **Capability presence** when whitespace-tokenisation produces exactly one token *and* that token matches the capability-name regex. Satisfied iff at least one enabled aspect declares the token in its `provides:`.
    - Any other shape (zero, two, or more-than-three tokens; one token that is not a valid capability name) is a manifest-load error naming the offending predicate.

<!-- INV-aspect-provides-capability-name-format -->
3. **Capability name format.** A capability matches the regex `^[a-z][a-z0-9-]*$` (lowercase letters, digits, dashes; no underscores; starts with a letter). The aspect-name regex permits underscores, so an aspect-name-shaped predicate (which would route through the 3-token depth-predicate branch) cannot collide with a capability-name-shaped predicate.

<!-- INV-aspect-provides-resolution -->
4. **Resolution rule.** A capability-presence entry in `requires:` is satisfied when at least one *enabled* aspect (depth ≥ 1) in the consumer's `.kanon/config.yaml` declares that capability in its `provides:`. The check fires at `kanon init`, `aspect add`, and `aspect set-depth` — the same gates that evaluate depth predicates today.

<!-- INV-aspect-provides-removal-check -->
5. **Removal check.** `kanon aspect remove <aspect>` refuses if removing the aspect would leave another *enabled* aspect with an unsatisfied capability-presence predicate. The error names the consumer aspect and the now-orphaned capability — symmetric with the existing depth-predicate removal check.

<!-- INV-aspect-provides-info-surfaces -->
6. **`aspect info` surfaces `provides:`.** `kanon aspect info <name>` prints a `Provides: <list>` line (or `(none)`) after the existing `Requires:` line. The `Requires:` listing already shows the raw predicate strings, so capability-presence predicates appear there alongside depth predicates without extra rendering work.

<!-- INV-aspect-provides-ci-validates-completeness -->
7. **CI validation.** `ci/check_kit_consistency.py` hard-fails if any capability-presence predicate in any aspect's `requires:` references a capability that no aspect in the same kit provides. This catches typos and dangling references at maintainer build time, before the kit ships to consumers. Depth-predicate references to unknown aspect names are caught the same way.

<!-- INV-aspect-provides-multiple-suppliers -->
8. **Multiple suppliers permitted.** Two aspects may legitimately both declare the same capability in their `provides:`. Resolution uses set-union semantics; the consumer is satisfied as long as *at least one* supplier is enabled. This is what allows future aspects (e.g., `lean-sdd`) to substitute for `sdd` without breaking downstream capability-presence predicates.

<!-- INV-aspect-provides-all-aspects-declare -->
9. **Every shipped aspect declares its discipline as a capability.** The kit's six aspects each declare at least one capability in their `provides:`, named after the discipline they package:
    - `sdd` provides `planning-discipline`, `spec-discipline`.
    - `worktrees` provides `worktree-isolation`.
    - `release` provides `release-discipline`.
    - `testing` provides `test-discipline`.
    - `security` provides `security-discipline`.
    - `deps` provides `dependency-hygiene`.
   No existing aspect's `requires:` is migrated to capability-presence form in this spec — adoption is opt-in and incremental.

<!-- INV-aspect-provides-no-silent-meaning-change -->
10. **No silent meaning change for existing `requires:` entries.** A 3-token predicate that parses today still parses identically. A 1-token predicate that today crashes (`ValueError: not enough values to unpack`) now becomes a capability-presence check, which is strictly more useful than a crash. No predicate that today *succeeds* changes meaning under this spec.

## Rationale

**Why capabilities and not just version pins.** A version pin couples the consumer to the supplier's identity; a capability decouples them. Renaming `sdd` → `methodology` is a breaking change today; in the capability model, as long as the new aspect declares the same capability, dependents are unaffected. This buys cheap insurance against the kind of rename that ADR-0009 (`agent-sdd` → `kanon`) was already costly enough to ship as a one-off.

**Why generalise `requires:` instead of adding a second field.** Two fields would mean kit authors mentally route every dependency through "is this a capability or a depth predicate?" twice — once choosing the field, once writing the predicate. Generalising puts both forms in one list, which matches the "all my dependencies live here" mental model. The token-count discriminator is unambiguous because the capability-name regex (no underscores, no whitespace, no operators) cannot match anything that would parse as a depth predicate's first token in a 3-token form. The risk of silently changing the meaning of an existing predicate is zero (INV-10) — every predicate that succeeds today succeeds identically; the only behavior change is that a 1-token predicate, which today raises a Python `ValueError`, now becomes a clean capability check.

**Why opt-in, no migration of existing `requires:` entries.** `worktrees`'s `requires: ["sdd >= 1"]` is genuinely a depth-predicate (worktrees needs the protocol infrastructure that activates at sdd depth ≥ 1, not an abstract capability). Rewiring it to `["worktree-isolation"]` would mis-state what worktrees actually depends on. The opt-in choice ships the registry without forcing a re-design of every existing dependency.

**Why declare `provides:` on every aspect.** Even if no consumer of the registry exists today, populating the registry across all six aspects has three benefits: (1) it pressure-tests the namespace against real-world disciplines (each aspect picks a name that survives review); (2) future aspects (in this kit or a fork) can immediately depend on capabilities without needing to wait for a separate "populate the registry" pass; (3) it makes the `aspect info` output discoverable — a contributor reading any aspect's info learns what capabilities exist.

**Why CI validates only kit-internal references.** A consumer's `.kanon/config.yaml` only ever references the kit's enabled aspects, so capability resolution at consumer time is mechanical. The hard-fail belongs at kit-build time, where a dangling reference indicates a *kit-author* mistake.

## Out of Scope

- **Per-depth `provides:` declarations.** A future spec may allow `provides:` to differ across depths (e.g., a capability supplied only at depth ≥ 2). v1 declares capabilities at the top-level aspect entry; semantics are "provided whenever the aspect is enabled at depth ≥ 1".
- **Capability versioning.** `provides: [planning-discipline]` is unversioned. If two aspects supply the same capability with subtly different semantics, that's a problem this spec does not solve. Versioning lands when there's evidence of need.
- **Migrating existing depth-predicate `requires:` entries to capability-presence form.** A separate plan can do that aspect by aspect when the design surface stabilises and a clear semantic mapping exists for each predicate.
- **Capability discovery commands.** No `kanon capability list` or `kanon capability who-provides`. `aspect info` covers the discovery need today.

## Decisions

- A new ADR-lite captures (a) the choice to generalise the existing `requires:` field via a token-count discriminator rather than introduce a parallel `requires-capabilities:` field, and (b) the opt-in migration stance for existing depth-predicate entries.
- Pattern instantiation under ADR-0012 (aspect model); no new ADR for the data shape itself.
