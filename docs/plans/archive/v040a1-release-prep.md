---
status: done
shipped-in: PR #83
slug: v040a1-release-prep
date: 2026-05-02
---

# Plan: v0.4.0a1 release preparation

Audit (critic agent `a1ee7c8c45bfad2c4`, 2026-05-02) found 2 critical + 7 major + 9 minor issues blocking the v0.4.0a1 cut. This plan addresses them in dependency order, batched into focused PRs to minimize blast radius if any wiring regresses.

## Goal

Clear all P0/P1 findings from the v0.3.1a2 → HEAD review so a clean `v0.4.0a1` tag can be cut with green gates including the wheel-shape gate and the substrate-independence gate.

## Background

ADR-0045 de-opinionation transition is complete in code (41 commits, 12k LOC) but ships:
- A reproducible test failure (`test_subprocess_emits_ok_sentinel`) that the CI workflow must have skipped or pytest collection drift hid.
- A wheel-build gate (`scripts/check_package_contents.py`) that requires a file the kit no longer produces (`kanon/kit/kit.md`, retired in Phase A.3).
- An ADR-0042 commitment ("canonical wording on `kanon verify --help`") the substrate doesn't honour.
- Forward-version mishandling in `kanon migrate` (silent corruption on `schema-version: 5`).
- README still describing v0.3 kit framing.
- `kanon init` writing v3-shape configs (forces immediate `kanon migrate`).
- Spec/impl error-code drift: `dialect-grammar.md` promises codes the impl doesn't emit.
- `_parse_contract_frontmatter` crashes on non-UTF-8 contracts (uncaught `UnicodeDecodeError`).
- No version bump in `src/kanon/__init__.py` despite the CHANGELOG `## [Unreleased]` containing a major-rewrite worth of entries.
- `_aspect_path()` legacy fallback returns dead paths when `kanon_reference` is absent — silently breaks ADR-0044's substrate-independence claim.

## Scope

In scope: all 2 critical + 7 major findings + 1 minor (`_aspect_path` legacy fallback, escalated because it falsifies ADR-0044). Plus the version bump and CHANGELOG renaming required to actually cut the release.

Out of scope (intentional, deferred to a `v040a1-followup` plan):
- Stale module docstrings (`_dialects`, `_realization_shape`, `_composition`).
- 7 reference-manifest header comments citing old paths.
- CHANGELOG line-ref drift (annotative; CHANGELOG is append-only).
- Design doc `${test_cmd}` placeholders in `docs/design/preflight.md`.
- 9 spec/design files referencing old `src/kanon/kit/aspects/` path (these are normative; need a separate sweep with publisher-facing review).
- Cardinality test for `len(V1_DIALECT_VERBS) == 9`.
- Coverage gap on `invalid-realization-shape` error path.

Out of scope, permanently:
- Bare-name shorthand removal (deprecation horizon not yet ratified).
- Per-phase release tags retroactively (cannot rewrite history).

## Acceptance criteria

- AC1: Full pytest suite passes (`956 passed, 5 deselected` or similar — no failures).
- AC2: `python scripts/check_package_contents.py --wheel <built-wheel> --tag v0.4.0a1` exits 0 against a freshly built wheel.
- AC3: `kanon verify --help` output contains the canonical ADR-0042 §1 wording (positive claim + 4 MUST-NOTs) verbatim or by direct citation.
- AC4: `kanon migrate --target <dir-with-schema-version-5>` exits non-zero with a `schema-version` ClickException; does not write a hybrid file.
- AC5: `kanon init <fresh-dir>` produces `.kanon/config.yaml` containing `schema-version: 4` and `kanon-dialect: "2026-05-01"` keys.
- AC6: README's first 80 lines describe the protocol-substrate framing per ADR-0048; Quickstart uses `--profile` or full `kanon-<local>` aspect names; no `--tier 1` recommendation; no bare-name examples.
- AC7: `_dialects.validate_dialect_pin` raises a typed exception (or surfaces structured findings) carrying `code: missing-dialect-pin` / `code: unknown-dialect` matching `docs/specs/dialect-grammar.md`. `_realization_shape` and `_composition` codes match the spec, OR the spec is amended to match the impl (decision in the relevant batch).
- AC8: `_parse_contract_frontmatter` returns a `ReplayError` with `code: invalid-contract-encoding` on non-UTF-8 input rather than raising `UnicodeDecodeError`. Test added.
- AC9: `src/kanon/__init__.py` declares `__version__ = "0.4.0a1"`; `.kanon/config.yaml` `kit_version` matches; CHANGELOG `## [Unreleased]` renamed to `## [0.4.0a1] — 2026-05-02` with a fresh empty `## [Unreleased]` heading above.
- AC10: With `kanon_reference` masked AND no overlay set, `_aspect_path("kanon-sdd")` returns a structured error or the substrate refuses to load gracefully — does not silently return a dead path. Test added.
- AC11: All 8 standalone gates green at HEAD (verify, links, foundations, kit_consistency, invariant_ids, packaging_split, verified_by, substrate_independence).

## Steps (batched into 4 PRs to limit blast radius)

### PR 1 — fix-failing-test (critical, unblocks everything else)

Single-file fix; should land first so subsequent PRs run against a green baseline.

1. Fix `tests/scripts/test_check_substrate_independence.py:34` — replace `from ci import check_substrate_independence` with the `load_ci_script` fixture pattern that the file's other 3 tests use.
2. Run `pytest tests/scripts/test_check_substrate_independence.py -v` — must show 4 passed.
3. Run full pytest — must show same passes count as before the fix plus 1.
4. Commit + push + PR + merge.

### PR 2 — release-gate-corrections (critical + version bump + ADR-0042 wiring)

These three are tightly coupled — the version bump is meaningless if the wheel gate blocks the tag, and the ADR-0042 wiring is required for the v0.4.0a1 release per ADR-0042's own Consequences §Substrate-side.

1. `scripts/check_package_contents.py:49` — remove `"kanon/kit/kit.md",` from `_CORE_REQUIRED_FILES`. Add gate-test (`tests/scripts/test_check_package_contents.py`) asserting kit.md is NOT required.
2. `src/kanon/__init__.py` — bump `__version__` to `"0.4.0a1"`.
3. `.kanon/config.yaml` — bump `kit_version` to `0.4.0a1`.
4. `CHANGELOG.md` — rename `## [Unreleased]` to `## [0.4.0a1] — 2026-05-02`; insert fresh empty `## [Unreleased]` above.
5. `src/kanon/cli.py` — `verify` command docstring updated to embed canonical ADR-0042 §1 wording (positive claim + 4 MUST-NOTs). Add a constant `_ADR_0042_VERIFY_SCOPE` so the same text can be re-used in `_verify.py` error messages and `kanon contracts validate` reports.
6. New test `tests/test_cli.py::test_verify_help_carries_adr_0042_wording` asserting `kanon verify --help` output contains the immutable phrases.
7. Build wheel: `uv build --wheel`. Run `.venv/bin/python scripts/check_package_contents.py --wheel dist/kanon_kit-0.4.0a1-py3-none-any.whl --tag v0.4.0a1` — must exit 0.
8. Commit + push + PR + merge.

### PR 3 — runtime-correctness (the 4 functional bugs)

1. `kanon migrate` future-schema guard — `cli.py:1395` (the v3→v4 augmentation block): add `elif schema_version > 4: raise click.ClickException("unknown schema-version {n}; this kanon does not know how to migrate forward")`. Test in `tests/test_cli_migrate.py`.
2. `kanon init` writes v4-shape config — `cli.py:_write_config` (or wherever the new-config write happens): emit `schema-version: 4`, `kanon-dialect: "2026-05-01"` for new configs. Add hint on empty-aspects path: `"Project scaffolded with no aspects. Try: kanon init . --profile team or --aspects kanon-sdd:1"`. Tests: assert config shape + hint text.
3. `_parse_contract_frontmatter` UTF-8 guard — `src/kanon/_resolutions.py:369`: wrap `read_text` in try/except `(UnicodeDecodeError, OSError)` → append `ReplayError(code="invalid-contract-encoding", contract=contract_id, reason=str(exc))` and return. Test with synthetic binary contract fixture.
4. `_aspect_path()` legacy fallback fix — `src/kanon/_manifest.py:721`: when `kanon_reference` import fails AND aspect is `kanon-*`, raise `click.ClickException("kanon-core cannot serve kanon-* aspects without kanon-aspects installed; install kanon-kit or kanon-aspects")` instead of returning a dead `_kit_root() / aspects / <slug>` path. Test: mask `kanon_reference`, call `_aspect_path("kanon-sdd")`, assert exception with helpful message.
5. Commit + push + PR + merge.

### PR 4 — error-code reconciliation (spec/impl drift)

**Direction: align impl to spec, not vice versa.** `docs/specs/dialect-grammar.md` is the public contract; `acme-` publishers will write tooling against the spec's codes. Renaming the spec to fit an inconvenient impl is a shortcut that violates `P-specs-are-source` and bakes implementation-state into the public surface. The impl's tests are easier to migrate than every future publisher's tooling.

1. **`_dialects.py`**: replace `click.ClickException` with structured findings. Introduce `DialectError` dataclass with `code: str` (`missing-dialect-pin` | `unknown-dialect`), `source: str | None`, `message: str`. `validate_dialect_pin()` raises a typed `DialectPinError(click.ClickException)` carrying the structured `code`. Caller in `_load_aspects_from_entry_points` re-raises with the code preserved in error message. Update `tests/test_dialects.py` to assert on `code` field.
2. **`_realization_shape.py`**: rename `ShapeValidationError.code` values from `{invalid-verb, invalid-evidence-kind, invalid-stage, unknown-key}` to a spec-aligned set. The spec calls these collectively `shape-violation`; the impl's finer-grained codes are useful diagnostic detail and SHOULD be preserved as a `subcode:` field. New shape: `code: "shape-violation"`, `subcode: "invalid-verb"` etc. Update `tests/test_realization_shape.py` to assert `code: shape-violation` + `subcode: <existing>`.
3. **`_realization_shape.py` parse failures**: `parse_realization_shape()` currently raises `click.ClickException` for missing `realization-shape:` block when wired in. Spec calls this `code: missing-realization-shape` and `code: invalid-realization-shape`. Surface as findings (or as a typed exception with `code:` attribute readable by callers in `_resolutions._validate_shape_against_contract`).
4. **`_composition.py`**: rename `composition-cycle` → `replacement-cycle` per spec line 41. Update `tests/test_composition.py`. Verify `kanon contracts validate` output emits the spec-aligned code.
5. **`docs/specs/dialect-grammar.md`**: add a normative table mapping each `code:` to its emitting module + symbol (creates a structural link between spec and impl so future drift fails a gate). Add a new gate or test that grep-asserts every spec-listed code appears verbatim in the impl source.
6. **README rewrite** — replace v0.3 kit framing with ADR-0048 protocol-substrate framing in first 80 lines; rewrite Quickstart to use `--profile solo` / `--aspects kanon-sdd:1`; remove all bare-name examples (or convert to `kanon-<local>` form); update narrative throughout to "protocol substrate" vocabulary.
7. New test asserting README first-80-lines do NOT contain phrases `"kit"` (as standalone word, not `"kanon-kit"`), `"--tier"`, or bare names like ` sdd ` / ` worktrees ` (with spaces around them so `kanon-sdd` doesn't trip).
8. Commit + push + PR + merge.

**Note:** PR 4 is the largest and most invasive. If size becomes a review burden, split into PR 4a (impl error-code reconciliation) + PR 4b (README rewrite + spec normative-table addition). Decision deferred to PR-4 execution time based on diff size.

## Verification

Per-PR: 8 gates green + full pytest passes.

Pre-tag: `uv build --wheel`, then `python scripts/check_package_contents.py --wheel <built> --tag v0.4.0a1` → exit 0; `python scripts/check_substrate_independence.py` → exit 0; `kanon verify .` against the kanon repo itself → exit 0.

## Out of scope, deferred to `v040a1-followup`

After v0.4.0a1 ships, follow-up plan addresses the 9 minor findings + the additional spec/design path-drift sweep (9 files). These are paper-cuts; not release blockers.
