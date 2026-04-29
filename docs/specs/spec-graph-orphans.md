---
status: accepted (lite)
date: 2026-04-25
target-release: v0.3
realizes:
  - P-cross-link-dont-duplicate
  - P-verification-co-authored
serves:
  - vision
fixtures:
  - tests/test_graph_orphans.py
  - tests/test_graph.py
invariant_coverage:
  INV-spec-graph-orphans-cli-surface:
    - tests/test_graph_orphans.py::test_inv1_cli_text_default_no_orphans
    - tests/test_graph_orphans.py::test_inv1_cli_json_status_ok
    - tests/test_graph_orphans.py::test_inv1_type_filter_restricts_namespace
  INV-spec-graph-orphans-definition:
    - tests/test_graph_orphans.py::test_inv2_unreferenced_principle_is_orphan
    - tests/test_graph_orphans.py::test_inv2_principle_referenced_by_live_spec_is_not_orphan
    - tests/test_graph_orphans.py::test_inv2_persona_with_outbound_stresses_is_not_orphan
    - tests/test_graph_orphans.py::test_inv2_capability_orphan_when_no_requires_predicate
    - tests/test_graph_orphans.py::test_inv2_capability_consumed_by_requires_is_not_orphan
  INV-spec-graph-orphans-status-scope:
    - tests/test_graph_orphans.py::test_inv3_deferred_spec_does_not_save_principle_from_orphan
    - tests/test_graph.py::test_inbound_live_excludes_deferred_source
    - tests/test_graph.py::test_inbound_live_includes_accepted_source
    - tests/test_graph.py::test_superseded_spec_does_not_contribute_inbound
  INV-spec-graph-orphans-self-orphan-rule:
    - tests/test_graph_orphans.py::test_inv4_deferred_spec_self_orphan_rule
    - tests/test_graph_orphans.py::test_inv4_superseded_spec_is_excluded_too
  INV-spec-graph-orphans-exempt-frontmatter:
    - tests/test_graph_orphans.py::test_inv5_orphan_exempt_node_listed_with_flag
    - tests/test_graph.py::test_orphan_exempt_helpers
  INV-spec-graph-orphans-no-thresholds:
    - tests/test_graph_orphans.py::test_inv6_no_fail_on_orphan_flag_exists
  INV-spec-graph-orphans-output-shape:
    - tests/test_graph_orphans.py::test_inv7_text_output_one_line_per_orphan
    - tests/test_graph_orphans.py::test_inv7_json_shape
  INV-spec-graph-orphans-shared-graph-load:
    - tests/test_graph.py::test_real_repo_loads_without_error
    - tests/test_graph.py::test_real_repo_has_known_aspects
    - tests/test_graph.py::test_real_repo_has_known_principles
  INV-spec-graph-orphans-exit-code:
    - tests/test_graph_orphans.py::test_inv9_exit_code_zero_with_orphans
---
# Spec: `kanon graph orphans` — find unreferenced nodes in the cross-link graph

## Intent

Provide a CLI report listing principles, personas, specs, and capabilities that have no inbound references in the cross-link graph. Orphans accumulate silently — a principle that no spec `realizes:`, a persona that no spec `stressed_by:`s, a capability that no aspect `requires:` — and their persistence makes it harder to reason about which artifacts are load-bearing. This spec replaces the manual approach (`grep` over each artifact) with a typed graph traversal.

This spec was extracted from the broader `spec-graph-tooling.md` umbrella when that spec was split. The rename and invariant-diff capabilities live in their own specs (`spec-graph-rename.md`, `spec-graph-diff.md`).

## Invariants

<!-- INV-spec-graph-orphans-cli-surface -->
1. **CLI surface.** `kanon graph orphans [--type <namespace>] [--format json|text]`. With no `--type`, the report covers every namespace that participates in the cross-link graph (principle, persona, spec, capability — see §Scope). With `--type <namespace>`, the report is filtered to that namespace. The default `--format` is `text`; `--format json` emits a machine-readable report mirroring the `kanon verify` JSON shape.

<!-- INV-spec-graph-orphans-definition -->
2. **Orphan definition — no inbound edges.** A node is an orphan when no other live artifact in the graph cites it via any of the typed edge fields:
    - **Principles**: orphan iff no spec lists the principle slug under `realizes:`.
    - **Personas**: orphan iff no spec lists the persona slug under `stressed_by:` AND the persona's own `stresses:` list points at no live spec or principle.
    - **Specs**: orphan iff (a) no plan references the spec via `serves:` (frontmatter or prose link target), AND (b) no other spec references it as a dependency edge under `serves:` or via `INV-*` cross-references.
    - **Capabilities**: orphan iff the capability appears in some aspect's `provides:` but no aspect's `requires:` lists it as a 1-token capability-presence predicate.

<!-- INV-spec-graph-orphans-status-scope -->
3. **Live-artifact scope.** Only live artifacts contribute inbound edges. A spec with `status: deferred` is not load-bearing yet; references from a deferred spec do NOT save a principle from being orphaned. Live statuses for purposes of this check: `accepted`, `accepted (lite)`, `provisional`, `draft`. Excluded: `deferred`, `superseded`. The orphan count is therefore stable against the deferred-spec backlog.

<!-- INV-spec-graph-orphans-self-orphan-rule -->
4. **A deferred spec is itself never reported as an orphan.** Deferred specs (`status: deferred`) are roadmap entries by design — no plan `serves:` them yet because work hasn't started. They are excluded from the orphan-spec list. They reappear as orphan candidates only after promotion to `draft` if no plan picks them up.

<!-- INV-spec-graph-orphans-exempt-frontmatter -->
5. **Explicit opt-out via `orphan-exempt:`.** A node may declare `orphan-exempt: true` in its frontmatter to opt out of the orphan check. This is intended for principles that govern agent conduct rather than any specific feature (e.g., `P-prose-is-code` may not be `realizes:`d by any spec but is core to the kit's identity). The exemption MUST include an `orphan-exempt-reason:` field with a one-sentence rationale; both fields are validated by the existing CI machinery (extension to `ci/check_foundations.py`).

<!-- INV-spec-graph-orphans-no-thresholds -->
6. **No "warn after N releases / fail after M" thresholds.** The umbrella spec floated configurable thresholds; this spec drops them. Orphan detection is a report; the consumer decides what to do with the report. Future evolution can add CI-failure semantics if a real consumer demand emerges.

<!-- INV-spec-graph-orphans-output-shape -->
7. **Output shape.**
    - **Text mode** (default): one line per orphan, prefixed by namespace and slug, e.g. `principle: P-prose-is-code (orphan-exempt: agent conduct stance)`. Exempt nodes are listed but flagged so reviewers can see they were excluded by design.
    - **JSON mode**: top-level object with `{"orphans": {<namespace>: [{"slug": ..., "exempt": bool, "reason": ...}, ...]}, "status": "ok"}`. Status is always "ok" — orphans are informational, not errors. The `exempt` field is true when the node carries `orphan-exempt: true`.
    - Both modes are stable across runs (slugs sorted alphabetically within each namespace).

<!-- INV-spec-graph-orphans-shared-graph-load -->
8. **Reuses shared graph-load primitive.** The `_graph.py` module introduced for `kanon graph rename` exposes a `build_graph(root) -> GraphData` function returning typed nodes and edges. `kanon graph orphans` consumes that primitive directly; no separate frontmatter scanner is added. This dependency is the practical reason this spec lands in the same release as `spec-graph-rename.md`.

<!-- INV-spec-graph-orphans-exit-code -->
9. **Exit code 0 when there are orphans.** Orphans are not errors; the command always exits 0 unless the graph itself is malformed (broken frontmatter, unparseable file). Malformed-graph exits with non-zero and the report does not enumerate orphans for that namespace. Consumers can build their own CI gate by piping `--format json` and asserting on the count.

<!-- INV-spec-graph-orphans-consumers-of-bridge -->
10. **Foundation for `consumers-of`.** The graph-load primitive (INV-8) plus the inbound-edge index used by orphan detection together provide the data structure that the deferred `expand-and-contract-lifecycle` spec needs for its `consumers-of <slug>` query. That query is not a v0.3 deliverable but is unblocked by this spec's machinery — a future small spec can expose it as a separate CLI verb.

## Rationale

**Why no thresholds.** "Warn after N releases, fail after M" was hand-waved in the umbrella spec — release was undefined, the kit has no persistent counter for "how many releases since this principle was first orphaned", and the honest interpretation requires every consumer to set their own policy. Reports are honest infrastructure; thresholds invented without grounding aren't. If a real consumer later wants CI to fail on orphans, they pipe `--format json` through `jq` or build their own gate.

**Why `orphan-exempt:` is required, not implicit.** Without an opt-out, the first conduct principle (e.g., `P-prose-is-code`) becomes an unresolvable orphan and the report becomes noisy. Without a *required reason*, exemptions accumulate without rationale and the orphan count becomes meaningless. The required `orphan-exempt-reason:` field forces an audit trail at the moment of exemption.

**Why deferred specs are excluded from inbound-edge contribution AND from orphan reporting.** Both directions matter. Deferred specs reference principles in their `realizes:`; allowing those references to save principles from orphan status means a principle deferred forever still appears load-bearing. Conversely, deferred specs naturally have no inbound `serves:` edges — including them in the orphan list would flag every roadmap entry as broken. INV-3 + INV-4 together close both gaps.

**Why no `--fail-on-orphan` flag.** Adding a CI-failure flag invites the question of whether a default policy should ship. The honest answer is "no, every project has different orphan tolerance"; the corollary is that the report itself shouldn't take a side. Consumers gate via `jq -e '.orphans.principle | length == 0'` or equivalent.

## Out of Scope

- **CI-fail flag** — see Rationale. Consumers gate via JSON pipeline.
- **Threshold-based warnings** — see INV-6. Future evolution if demand emerges.
- **`consumers-of` query** — INV-10 says the data structure is ready, but exposing it as a CLI verb belongs to a separate spec (likely accompanying expand-and-contract-lifecycle promotion).
- **Cycle detection in the graph** — orphans are a node-level property; cycles are an edge-level property. Cycle detection is a separate concern, possibly a future spec.
- **Inbound edges from prose** — only structurally typed edges count. A principle mentioned in a paragraph but not under any `realizes:` field is treated as orphan. (The rationale: prose mentions are unstructured and prone to drift; the structured edge IS the contract.)
- **Detecting unreferenced ADRs** — ADRs are immutable historical records by design (per `docs/decisions/README.md` § What is an ADR); they don't have inbound-edge semantics in the same way as principles. Out of scope.
- **Detecting unreferenced plans** — plans are permanent records of how features were built; "no inbound edge" doesn't apply.

## Decisions

- The `orphan-exempt:` and `orphan-exempt-reason:` frontmatter fields are validated by extending `ci/check_foundations.py` (the existing principle/persona validator). No new ADR — frontmatter-field additions are routine.
- This spec depends on `spec-graph-rename.md` for the `_graph.py` primitive (INV-8). They are intended to ship in the same release.
- Pattern instantiation under ADR-0026 (capability registry) for the capability-orphan rule.
