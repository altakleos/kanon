---
status: accepted
design: "Follows ADR-0010"
date: 2026-04-22
realizes:
  - P-prose-is-code
  - P-specs-are-source
stressed_by:
  - onboarding-agent
  - solo-engineer
fixtures:
  - tests/test_protocols.py
  - tests/test_kit_integrity.py
invariant_coverage:
  INV-protocols-location:
    - tests/test_protocols.py::test_sdd_protocols_directory_exists
    - tests/test_protocols.py::test_protocol_byte_equals_repo_canonical
  INV-protocols-frontmatter-schema:
    - tests/test_protocols.py::test_protocol_has_required_frontmatter_keys
  INV-protocols-tier-gating:
    - tests/test_protocols.py::test_protocol_depth_min_matches_sub_manifest
  INV-protocols-discoverability:
    - tests/test_cli.py::test_protocols_index_marker_present_tier1_plus
    - tests/test_cli.py::test_protocols_index_present_at_tier_0
  INV-protocols-byte-equality:
    - tests/test_protocols.py::test_protocol_byte_equals_repo_canonical
  INV-protocols-additive-across-tier-up:
    - tests/test_cli.py::test_tier_up_additive_only
    - tests/test_cli.py::test_tier_set_below_current_is_noop
  INV-protocols-no-runtime-dispatch:
    - tests/test_protocols.py
---
# Spec: Protocol layer — prose-as-code judgment procedures

## Intent

Define `.kanon/protocols/` as a first-class layer of the kit: prose documents an operating LLM agent reads on demand to execute multi-step judgment procedures (tier-up decisions, verify-report triage, spec review, …). Protocols are code — versioned, byte-checked, discoverable via an AGENTS.md marker section — but the runtime is the agent, not an interpreter.

The layer exists because some operations are judgment-shaped, not algorithm-shaped: deciding *whether* to tier up, interpreting *which* verify findings matter most, reviewing a spec for ambiguity. Hardcoding these into the Python CLI would either fail (judgment doesn't compile) or produce brittle heuristics. Letting the agent improvise loses reproducibility. Protocols split the difference — deterministic structure, LLM-interpreted steps.

## Invariants

<!-- INV-protocols-location -->
1. **Location is `.kanon/protocols/` in consumer repos** and `src/kanon/kit/protocols/` in the kit source. Every file in the consumer path has a byte-identical mirror in the kit source, enforced by `ci/check_kit_consistency.py`.
<!-- INV-protocols-frontmatter-schema -->
2. **Frontmatter schema.** Every protocol file has YAML frontmatter with four required keys:
   - `status`: one of `draft | accepted | deferred | provisional | superseded`.
   - `date`: ISO-8601 date (YYYY-MM-DD).
   - `tier-min`: the lowest tier at which the protocol is scaffolded (integer 0–3).
   - `invoke-when`: one sentence stating the trigger condition.
<!-- INV-protocols-tier-gating -->
3. **Tier gating.** `tier-min` must equal the tier the protocol first appears in per `src/kanon/kit/manifest.yaml`. A protocol declared in the manifest under `tier-N.protocols` has `tier-min: N` in its frontmatter.
<!-- INV-protocols-discoverability -->
4. **Discoverability.** At tier ≥ 1, the consumer's `AGENTS.md` contains a `<!-- kanon:begin:protocols-index -->` / `<!-- kanon:end:protocols-index -->` marker block listing every active protocol by name, trigger, and tier-min. The block is regenerated from the manifest on every `init` / `tier set` / `upgrade`.
<!-- INV-protocols-byte-equality -->
5. **Byte-equality with kit source.** `kanon verify` fails if `.kanon/protocols/<name>.md` differs byte-for-byte from the kit's `src/kanon/kit/protocols/<name>.md` (for the installed `kit_version`). User edits to protocols are signalled as drift, not silently accepted.
<!-- INV-protocols-additive-across-tier-up -->
6. **Additive across tier-up.** Tier-up migrations add new protocol files without touching existing ones. Tier-down leaves protocol files on disk (per ADR-0008, tier-down is non-destructive); the `protocols-index` marker removes the entry, but the file remains until the user deletes it.
<!-- INV-protocols-no-runtime-dispatch -->
7. **No runtime dispatch.** There is no `kanon protocol <name>` CLI subcommand in v0.1. Protocols are invoked by the operating agent reading the file; the CLI's role is scaffolding and integrity-checking only.

## Rationale

Byte-equality (INV-protocols-byte-equality) enforces that the protocol text the agent reads in a consumer repo matches what the kit authored. Without it, a consumer's protocol could silently drift from the documented behavior, and a fresh agent session would execute unknowable steps. This mirrors the same enforcement applied to `docs/sdd-method.md` and `_template.md` files (per `template-bundle.md` INV-template-bundle-tier3-canonical-with-repo, carried forward into `kit-bundle.md`).

The `tier-min` frontmatter field (INV-protocols-frontmatter-schema) is not just documentation — `ci/check_kit_consistency.py` cross-checks it against `manifest.yaml`, catching drift where a protocol is moved between tiers in the manifest but the frontmatter is forgotten.

The `protocols-index` marker block (INV-protocols-discoverability) is the discovery mechanism. A fresh LLM session reading `AGENTS.md` sees the catalog inline and can invoke protocols without knowing the directory structure.

## Out of Scope

- Runtime dispatch (`kanon protocol <name>`) — deferred.
- Protocol versioning / supersession chains — a protocol file's `status: superseded` plus a new file suffices for v0.1; structured supersession (like ADRs) is deferred.
- Consumer-authored protocols. v0.1 ships three kit-authored protocols; consumer-side extensions are possible (any `.kanon/protocols/*.md` the agent reads) but not first-class until v0.2+.

## Decisions

See ADR-0010 (protocol-layer decision), ADR-0011 (kit-bundle refactor that makes the protocol layer cheap to add).
