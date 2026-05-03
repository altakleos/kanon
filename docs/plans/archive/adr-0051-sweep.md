---
slug: adr-0051-sweep
status: done
owner: makutaku
created: 2026-05-03
related-adr: 0051
shipped-in: PR #102
---

# Plan — ADR-0051 distribution-rename sweep

## Context

ADR-0051 (accepted 2026-05-03 via PR #101) renamed two of the three planned distributions. The pre-rename names are quoted explicitly below since the whole point of this plan is to record the from→to mapping; do **NOT** sed across this file.

| Role | Pre-ADR-0051 name | Post-ADR-0051 name |
|------|-------------------|--------------------|
| Substrate kernel | (quoted: substrate) | `kanon-core` |
| Reference content | (quoted: reference) | `kanon-aspects` |
| Meta-package | `kanon-kit` | `kanon-kit` |

(The pre-rename names are intentionally written above as parenthetical descriptions rather than as the literal hyphenated tokens, to keep this plan idempotent under a sed sweep that targets those tokens.)

This sweep PR replaces the ~51 in-repo references to the old names. The actual three-package PyPI split is deferred (Hatch editable-install constraint per ADR-0050); this PR is doc + code-string replacement only.

## Scope

### In

Mechanical text-replacement across:

1. **ADR bodies** (immutable per ADR-0032; commit needs `Allow-ADR-edit:` trailer for each):
   - 0039, 0040, 0041, 0042, 0043, 0044, 0045, 0048, 0049

2. **Code** (functional changes — the substrate-independence allowed-dist-list per ADR-0040 governs runtime aspect-discovery):
   - `kernel/_manifest.py` (4 sites: validator allow-list — the previous tuple element for the reference distribution becomes `"kanon-aspects"`; 3 error-message strings)
   - `kernel/cli.py` (1 site: forward-compat error message)
   - `kernel/__init__.py` (1 site: module docstring)
   - `src/kanon_reference/__init__.py` (1 site: package docstring)
   - `scripts/check_substrate_independence.py` (1 site: script docstring header)
   - `tests/test_aspect_registry.py` (2 sites: fixture dist-name + error-message substring assertion)

3. **Foundational docs** (free-edit):
   - `docs/foundations/vision.md`, `de-opinionation.md`
   - `docs/foundations/principles/P-protocol-not-product.md`, `P-publisher-symmetry.md`, `P-runtime-non-interception.md`, `P-self-hosted-bootstrap.md`
   - `docs/foundations/personas/onboarding-agent.md`, `acme-publisher.md`, `solo-with-agents.md`

4. **Specs + design docs** (free-edit):
   - `docs/specs/dialect-grammar.md`, `release-cadence.md`, `substrate-self-conformance.md`
   - `docs/design/distribution-boundary.md`, `dialect-grammar.md`, `kernel-reference-interface.md`

5. **Repo top-level + project state**:
   - `README.md`
   - `.kanon/config.yaml`, `.kanon/recipes/reference-default.yaml` (only if the literal strings appear; repo state, not docs)

6. **Plans** (active/, where they describe forward-looking work — not strictly historical):
   - All `docs/plans/active/*.md` that mention the names. These are the migration plans and they describe future work; updating them keeps Phase A planning aligned with the post-ADR-0051 vocabulary.

### Out

- `src/kanon_reference/` directory rename — **explicitly deferred** by ADR-0051 §Consequences §Code (same Hatch editable-install constraint that produced ADR-0050; needs its own ADR).
- The Python module name `kanon_reference` (with underscore) — sed targets the hyphen variant only; underscore variant is not matched.
- The aspect-slug grammar (`kanon-sdd`, `kanon-testing`, etc.) — unchanged.
- The CLI command name `kanon` — unchanged.
- The entry-point group `kanon.aspects` — unchanged (preserved per ADR-0040 protocol contract).
- The published distribution `kanon-kit` — unchanged.
- `CHANGELOG.md` historical entries — they record what shipped with which name at write time; rewriting them would falsify history. Only `## [Unreleased]` (if it gains an entry for this rename PR) is in scope.
- This plan file itself — quoted from→to context must remain.
- ADR-0051 normative body (`docs/decisions/0051-distribution-naming.md`) — explicitly discusses both old and new names.
- Squash-merged ADR PRs / commit messages / git history — out of scope; immutable.

## Acceptance criteria

- AC1: `grep -rln` for the old hyphenated tokens across the in-scope files (per §Scope §In) returns zero matches afterward, EXCEPT in this plan, in `docs/decisions/0051-distribution-naming.md` (which discusses both old and new names normatively), and in `CHANGELOG.md` (which records the historical state).
- AC2: `grep -rln "kanon_reference"` count is unchanged (the underscore variant is the source-tree path; deferred).
- AC3: Full `pytest` passes — the substrate-independence allow-list change is exercised by `tests/test_aspect_registry.py`.
- AC4: `kanon verify .` status=ok.
- AC5: All 7 standalone gates green.
- AC6: Fidelity recaptured if any file in fidelity-watch list changed.

## Steps

1. Sed across the foundational, spec, design, plan, README files (free-edit):
   `find docs/foundations docs/specs docs/design docs/plans/active -name '*.md' -not -path '*/0051-*' -not -name 'adr-0051-sweep.md' | xargs sed -i ...`
   excluding `docs/decisions/0051-*.md`, this plan file, and CHANGELOG.md.
2. Sed across the ADR bodies (will need Allow-ADR-edit trailer):
   `sed -i ... docs/decisions/0039-*.md ... docs/decisions/0049-*.md` (excluding 0051).
3. Sed across the code files: `kernel/_manifest.py`, `kernel/cli.py`, `kernel/__init__.py`, `src/kanon_reference/__init__.py`, `scripts/check_substrate_independence.py`, `tests/test_aspect_registry.py`.
4. Sed across `.kanon/config.yaml` + `.kanon/recipes/reference-default.yaml`.
5. Verify `grep` count per AC1.
6. Run `pytest -q --no-cov` end-to-end.
7. Run `kanon verify .`.
8. If fidelity warns, run `kanon fidelity update .`.
9. Commit with `Allow-ADR-edit: 0039, 0040, 0041, 0042, 0043, 0044, 0045, 0048, 0049 — distribution rename per ADR-0051` trailer.
10. Push, PR, auto-merge.

## Risks

- **Sed self-corruption** (already encountered on first attempt): a plan that mentions both pre-rename and post-rename names gets sed-rewritten and the `from → to` table reads as `to → to`. Mitigation: write this plan's pre-rename names as parenthetical descriptions, never as the literal hyphenated tokens.
- **AC1 false positives**: a literal string in a regex pattern or test fixture might be intentional. Mitigation: post-sed grep for quoted-string occurrences and inspect each.
- **Code change runtime impact**: `_manifest.py`'s validator allow-list semantically governs which Python distributions may publish `kanon-*` aspect entry-points. After this PR the new name is allowed; the previous planned name is not. No published distribution exists at either name today (only `kanon-kit`), so there is no current consumer to break.
- **Plans/archive untouched**: Per the PR #98 convention, `docs/plans/archive/*.md` represent historical state-at-write and should not be edited. None appear in the audit list, so no risk.
