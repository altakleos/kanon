---
status: accepted
design: "Follows ADR-0025"
date: 2026-04-25
realizes:
  - P-prose-is-code
serves:
  - vision
fixtures:
  - tests/test_aspect_config.py
invariant_coverage:
  INV-aspect-config-set-config-command:
    - tests/test_aspect_config.py::test_set_config_idempotent_apart_from_timestamp
  INV-aspect-config-add-config-flag:
    - tests/test_aspect_config.py::test_aspect_add_config_flag_populates_config_at_enable_time
    - tests/test_aspect_config.py::test_aspect_add_config_flag_repeatable
  INV-aspect-config-yaml-scalar-parsing:
    - tests/test_aspect_config.py::test_parse_config_pair_yaml_scalar
    - tests/test_aspect_config.py::test_parse_config_pair_rejects_lists_and_mappings
  INV-aspect-config-key-format:
    - tests/test_aspect_config.py::test_parse_config_pair_rejects_bad_keys
  INV-aspect-config-schema-validation: []  # Phase A.4: kanon-testing's config-schema retired (per ADR-0048); the validation mechanism survives in _aspect_config_schema. Tests deferred until a project-aspect or acme-* publisher fixture declares a schema.
  INV-aspect-config-schema-optional:
    - tests/test_aspect_config.py::test_set_config_accepts_any_key_when_no_schema
  INV-aspect-config-config-schema-shape:
    - tests/test_aspect_config.py::test_malformed_config_schema_rejected_at_manifest_load
    - tests/test_aspect_config.py::test_malformed_config_schema_invalid_type_rejected
    - tests/test_aspect_config.py::test_malformed_config_schema_unknown_field_rejected
  INV-aspect-config-atomic-write:
    - tests/test_aspect_config.py::test_set_config_clears_sentinel_on_success
    - tests/test_aspect_config.py::test_set_config_persists_sentinel_on_mid_write_failure
  INV-aspect-config-info-surfaces-schema:
    - tests/test_aspect_config.py::test_aspect_info_omits_config_block_when_no_schema
  INV-aspect-config-error-aspect-not-enabled:
    - tests/test_aspect_config.py::test_set_config_errors_when_aspect_not_enabled
---
# Spec: Aspect configuration values

## Intent

Aspects already declare a `config:` block in `.kanon/config.yaml` per ADR-0012, but the CLI exposes no way for a consumer to set values into it. Today the only way to populate `aspects.<name>.config.<key>` is to hand-edit YAML — which is fragile, agent-unfriendly, and at odds with the kit's "everything goes through `kanon`" promise.

This spec adds two CLI surfaces:

1. `kanon aspect set-config <target> <name> <key>=<value>` — set or update one config key on an enabled aspect.
2. `--config <key>=<value>` (repeatable) on `kanon aspect add` — populate config keys at enable time.

The shape of `aspects.<name>.config` in the on-disk schema is unchanged; only the *write paths* are new. ADR-0012 advertised both surfaces in its "Decision" section but they were never implemented; this spec is the contract that retroactively makes that ADR honest.

## Invariants

<!-- INV-aspect-config-set-config-command -->
1. **`set-config` command.** `kanon aspect set-config <target> <name> <key>=<value>` exists. It requires the aspect to be enabled (depth > 0) at `<target>`. Each invocation sets exactly one key. The command is idempotent — running it twice with the same arguments leaves config.yaml byte-identical save for the refreshed `enabled_at` timestamp on `aspects.<name>`.

<!-- INV-aspect-config-add-config-flag -->
2. **`--config` flag on `aspect add`.** `kanon aspect add <target> <name> [--config <key>=<value> ...]` accepts the flag zero or more times. Each occurrence sets one key in `aspects.<name>.config` at enable time. The flag is mutually consistent with `--depth`: both may be provided in the same invocation.

<!-- INV-aspect-config-yaml-scalar-parsing -->
3. **YAML-scalar value parsing.** The `<value>` half of `<key>=<value>` is parsed as a YAML scalar via `yaml.safe_load`. `coverage_floor=80` stores `80` (int); `flag=true` stores `True` (bool); `name=foo` stores `"foo"` (str); `regex=^[a-z]+$` stores the string `"^[a-z]+$"`. Quoting follows YAML rules: `pin="==1.2"` stores `"==1.2"` (string). Lists and mappings are not supported on the CLI — values containing `,`, `[`, `]`, `{`, or `}` are rejected with a single-line error.

<!-- INV-aspect-config-key-format -->
4. **Key format.** A `<key>` matches the regex `^[a-z][a-z0-9_-]*$` (lowercase, starts with letter, dashes and underscores allowed). Anything else is rejected with a single-line actionable error naming the offending key.

<!-- INV-aspect-config-schema-validation -->
5. **Schema validation against `config-schema:`.** When an aspect's sub-manifest declares a `config-schema:` mapping under `src/kanon/kit/aspects/<name>/manifest.yaml`, every key set via `set-config` or `--config` must appear in the schema, and the parsed YAML-scalar value must satisfy the schema's declared type. Unknown keys are rejected; type mismatches are rejected. Each rejection is a single-line error naming the key, the expected type (when applicable), and the offending value.

<!-- INV-aspect-config-schema-optional -->
6. **Schema is optional.** When an aspect's sub-manifest does *not* declare `config-schema:`, any well-formed `<key>=<value>` is accepted. Removing or relaxing a schema is non-destructive — existing keys in consumer `config.yaml` files are preserved verbatim.

<!-- INV-aspect-config-config-schema-shape -->
7. **`config-schema:` shape.** When present, `config-schema:` is a mapping from key name to a small descriptor: at minimum a `type:` field whose value is one of `string`, `integer`, `boolean`, or `number`. An optional `default:` field documents the aspect's compiled-in default (informational; the CLI does not auto-populate defaults). An optional `description:` field is human-readable text surfaced by `kanon aspect info`.

<!-- INV-aspect-config-atomic-write -->
8. **Atomic writes.** `aspect set-config` writes config.yaml via the same crash-consistent atomicity contract used by `aspect add` / `aspect remove` / `aspect set-depth` (ADR-0024): a `.kanon/.pending` sentinel wraps the write, `config.yaml` is the only mutated file, and the sentinel is cleared after a successful `_write_config`.

<!-- INV-aspect-config-info-surfaces-schema -->
9. **`aspect info` surfaces the schema.** `kanon aspect info <name>` prints each declared `config-schema:` key with its type, default (when set), and description (when set). Aspects with no schema show the existing depth-by-depth file/protocol counts unchanged.

<!-- INV-aspect-config-error-aspect-not-enabled -->
10. **`set-config` on a disabled aspect errors.** Running `set-config` against an aspect whose depth is 0 (or absent from the consumer's config) emits a single-line error directing the user to `kanon aspect add` first, and exits non-zero. `--config` on `aspect add` does not have this constraint — the aspect is being enabled in that same call.

## Rationale

**Why YAML-scalar parsing.** The `testing` aspect already stores `coverage_floor: 80` as an integer in its consumer config; if `set-config coverage_floor=80` stored the string `"80"` instead, the existing config-aware code in `ci/check_test_quality.py` would break or need a parallel string-handling path. YAML-scalar parsing makes the CLI's storage match the format an author would have hand-written. The narrow rejection of list / mapping syntax is a forcing function — anyone needing structured config can hand-edit YAML, but the common case (scalars) is safe and ergonomic.

**Why a schema is optional.** Mandating a schema would block experimental aspects from shipping without one. Optional-but-validated lets aspect authors add a schema only when the aspect's config has stabilized. The schema's job is not to prevent every misuse — it's to catch typos and type mistakes that would otherwise sit silently in `config.yaml` until something downstream blew up.

**Why the schema lives in the sub-manifest.** Aspects already own their per-depth manifests under `src/kanon/kit/aspects/<name>/manifest.yaml`. Adding a top-level `config-schema:` key keeps all aspect-author surface in one file. Verifying it costs one extra YAML parse during `_load_aspect_manifest` (already cached).

**Why `aspect set-config` is one key per call.** Multi-key `set-config <name> a=1 b=2 c=3` would either need shell-quoting gymnastics or a separate file-input mode. Single-key calls compose cleanly in shell scripts and agent transcripts. The `--config` repeatability on `aspect add` covers the bulk-set case.

## Out of Scope

- **Reading config values.** No `kanon aspect get-config <name> <key>`; consumers can `cat .kanon/config.yaml` or write a small helper. If demand emerges, a future spec adds it.
- **Removing a config key.** No `aspect unset-config`. Consumers needing to clear a key hand-edit YAML; the schema does not enforce key presence, only type when present.
- **Cascading aspect-config changes into AGENTS.md or kit.md.** Setting a config key does not re-render assembled views. AGENTS.md / kit.md aren't parameterised by aspect config today.
- **Migrating legacy v1 (tier-based) consumer configs.** v1 configs already auto-migrate to v2 on `kanon upgrade`; the new commands assume v2 shape.
- **List or mapping values on the CLI.** Explicitly rejected by INV-3 to keep the surface narrow. Aspect authors needing structured config either hand-edit YAML or split the value across multiple scalar keys.

## Decisions

- ADR-0012 advertised the surface; this spec is the contract.
- ADR-0024 governs atomic writes (INV-8).
- A new ADR-lite captures the YAML-scalar parsing decision and the optional-schema choice during implementation.
