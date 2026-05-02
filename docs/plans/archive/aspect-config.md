---
feature: aspect-config
serves: docs/specs/aspect-config.md
design: "ADR-0025-lite captures the YAML-scalar parse + optional-schema choice. Pattern instantiation: ADR-0024 (atomicity), ADR-0012 (aspect surface)."
status: done
date: 2026-04-25
---
# Plan: `kanon aspect set-config` and `aspect add --config`

## Context

Implements `docs/specs/aspect-config.md` (10 invariants). Adds two CLI write paths to `aspects.<name>.config.<key>`, optional schema validation, and `aspect info` schema rendering. ADR-0012 promised the surface; this plan delivers it.

## Tasks

### Schema parsing (manifest layer)

- [x] T1: Extend `_load_top_manifest` / `_load_aspect_manifest` validation in `src/kanon/_manifest.py` to accept an optional `config-schema:` key on each per-aspect sub-manifest. Each schema entry validates as a mapping with required `type:` (one of `string`, `integer`, `boolean`, `number`) and optional `default:` / `description:`. Unknown fields under a schema entry are rejected at load time. → `src/kanon/_manifest.py`

- [x] T2: Add `_aspect_config_schema(aspect_name) -> dict[str, dict[str, Any]] | None` returning the loaded schema (or `None` when the aspect declares none). → `src/kanon/_manifest.py`

### CLI value parsing

- [x] T3: Add `_parse_config_pair(raw: str, schema: dict[str, dict[str, Any]] | None) -> tuple[str, Any]` to `src/kanon/cli.py`. Splits on the first `=`, validates the key regex (`^[a-z][a-z0-9_-]*$`), parses the value via `yaml.safe_load`. Rejects values whose parsed form is a `list` or `dict`. When `schema` is non-None: rejects unknown keys; rejects values whose Python type does not match the declared schema type (`int` for `integer`, `str` for `string`, `bool` for `boolean`, `int|float` for `number`). Returns `(key, parsed_value)`. → `src/kanon/cli.py`

### CLI surface

- [x] T4: Add `kanon aspect set-config <target> <name> <pair>` Click command in `src/kanon/cli.py`. Validates the aspect is enabled (depth > 0) at `<target>`; loads schema; calls `_parse_config_pair`; updates `aspects_meta[aspect_name].config[key]`; writes config.yaml under sentinel; emits a single-line success message. Single key per call. → `src/kanon/cli.py`

- [x] T5: Add `--config` flag (multi-value, repeatable) to the existing `aspect add` Click command. For each occurrence, parse via `_parse_config_pair` against the aspect's schema, accumulate into a `config: dict[str, Any]`. The accumulated dict is passed through to the existing add-path so it lands as `aspects.<name>.config` in the freshly-stamped meta entry. → `src/kanon/cli.py`

- [x] T6: Extend `aspect info` rendering in `src/kanon/cli.py` to surface the schema when one is declared. After the existing depth-by-depth file/protocol counts, print a `Config keys:` block listing each schema key with its type, default (when set), and description (when set). When no schema is declared, behaviour is unchanged. → `src/kanon/cli.py`

### Test data + fixtures

- [x] T7: Add a `config-schema:` block to one experimental aspect's sub-manifest as a real-world fixture. The `testing` aspect already stores `coverage_floor: 80` in consumer configs; declare it in `src/kanon/kit/aspects/testing/manifest.yaml` with `type: integer` and a description. This serves as the spec's lived example and exercises the validation path. → `src/kanon/kit/aspects/testing/manifest.yaml`

### Tests

- [x] T8: `tests/test_aspect_config.py` covering INV-1 through INV-10. Concrete cases:
    - **INV-1**: `set-config testing coverage_floor=80` then `set-config testing coverage_floor=80` again is idempotent (config.yaml byte-identical except `enabled_at`).
    - **INV-2**: `aspect add testing --config coverage_floor=85` on a fresh project yields `aspects.testing.config.coverage_floor == 85`.
    - **INV-3**: scalar parsing — `flag=true` → `True` (bool), `n=42` → `42` (int), `name=foo` → `"foo"` (str), `pin="==1.2"` → `"==1.2"` (str). Reject `xs=[1,2]`, `m={a:1}`, and any value containing unescaped `,` `[` `]` `{` `}`.
    - **INV-4**: reject keys `Foo`, `1foo`, `foo bar`, empty string, with single-line errors naming the offending key.
    - **INV-5**: set-config `unknown_key=1` against `testing` (which has a schema) is rejected naming the key. Set-config `coverage_floor=hello` against `testing` is rejected naming the type mismatch.
    - **INV-6**: set-config against an aspect with NO `config-schema:` accepts any well-formed key. (Use `worktrees` or another schemaless aspect for this case.)
    - **INV-7**: an aspect manifest with a malformed `config-schema:` entry (e.g., missing `type:`) raises a clear error at manifest load time.
    - **INV-8**: a `.kanon/.pending` sentinel exists during the write and is gone after success; on simulated mid-write failure the sentinel persists.
    - **INV-9**: `aspect info testing` output contains the `coverage_floor` key, its `integer` type, and the description.
    - **INV-10**: `set-config testing coverage_floor=80` against a project where `testing` is at depth 0 (or absent) errors with a single-line message and exits non-zero.

- [x] T9: Update `tests/test_kit_integrity.py` (or add a new test file) asserting `_aspect_config_schema("testing")` round-trips — schema loaded from the manifest matches the on-disk YAML.

### Documentation

- [x] T10: Update `docs/decisions/0012-aspect-model.md` is impossible (ADRs are immutable). Instead, write **ADR-NNNN-lite** capturing the YAML-scalar parsing decision and the optional-schema choice. Reference ADR-0012 in the "Why" line. → `docs/decisions/00NN-aspect-config-parsing.md`

- [x] T11: Add ADR-NNNN to `docs/decisions/README.md`.

- [x] T12: Add this plan to `docs/plans/README.md`.

- [x] T13: Update `CHANGELOG.md` `## [Unreleased] / ### Added`:
    - `kanon aspect set-config <target> <name> <key>=<value>` and `aspect add --config <key>=<value>` for per-aspect configuration values. YAML-scalar parsing; optional `config-schema:` per aspect for validation.

### Self-host

- [x] T14: Run `kanon aspect set-config . testing coverage_floor=80` against the repo to populate the field via the new path (replacing whatever is there). Verify `kanon verify .` returns ok and `scripts/check_kit_consistency.py` returns exit 0 (kit consistency unaffected).

## Acceptance Criteria

- [x] AC1: `pytest` passes; full suite ≥ 90% coverage; new tests in T8/T9 all pass.
- [x] AC2: `mypy src/kanon` clean.
- [x] AC3: `ruff check src/ tests/ ci/` clean.
- [x] AC4: `python scripts/check_kit_consistency.py` returns exit 0.
- [x] AC5: `kanon verify .` returns `status: ok` against the repo.
- [x] AC6: `kanon aspect set-config . testing coverage_floor=80` succeeds and `.kanon/config.yaml` shows `aspects.testing.config.coverage_floor: 80` (int, not string).
- [x] AC7: `kanon aspect info testing` output contains a `Config keys:` block listing `coverage_floor` with type `integer`.
- [x] AC8: All 10 spec invariants have at least one test in `invariant_coverage:` in the spec frontmatter (added before promoting status from draft to accepted).

## Documentation Impact

- `CHANGELOG.md` `## [Unreleased] / ### Added` (T13).
- New ADR-lite at `docs/decisions/00NN-aspect-config-parsing.md` (T10–T11).
- `docs/specs/aspect-config.md` promoted from `draft` → `accepted` once tests cover all 10 invariants (status flip in same commit as the implementation lands or in the immediately following commit).
- `docs/plans/README.md` index entry (T12).
