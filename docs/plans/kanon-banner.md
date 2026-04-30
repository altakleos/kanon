---
feature: kanon-banner
serves: docs/specs/kanon-banner.md
design: docs/design/kanon-banner.md
status: in-progress
date: 2026-04-30
---
# Plan: `kanon` banner

## Context

ADR-free user-visible UX addition. Spec at `docs/specs/kanon-banner.md` (six invariants), design at `docs/design/kanon-banner.md` (single-source + template-substitution mechanism). This plan is the mechanical realization of that design.

The banner is the figlet `standard` rendering of `kanon`, frozen byte-for-byte:

```
  _  __                       
 | |/ /__ _ _ __   ___  _ __  
 | ' // _` | '_ \ / _ \| '_ \ 
 | . \ (_| | | | | (_) | | | |
 |_|\_\__,_|_| |_|\___/|_| |_|
                              
```

Three surfaces emit it: `kanon init` stderr, `kanon upgrade` stderr, top of scaffolded `AGENTS.md` inside a `<!-- kanon:begin:banner --> ... <!-- kanon:end:banner -->` marker block above the H1.

## Tasks

- [ ] T1: Create `src/kanon/_banner.py` containing the `_BANNER` constant and the `_should_emit_banner(quiet: bool) -> bool` helper. → `src/kanon/_banner.py` (new file).
- [ ] T2: Add the empty banner marker block at the top of `src/kanon/kit/agents-md-base.md`, above the existing `# AGENTS.md — ${project_name}` heading. → `src/kanon/kit/agents-md-base.md`.
- [ ] T3: In `_assemble_agents_md` add a `_replace_section(text, "banner", _BANNER)` call alongside the existing `hard-gates` and `protocols-index` substitutions. Import `_BANNER` from `_banner`. → `src/kanon/_scaffold.py` (around line 425). (depends: T1, T2)
- [ ] T4: Add `--quiet` / `-q` flag to `kanon init` and emit the banner via `click.echo(_BANNER, err=True)` when `_should_emit_banner(quiet)` is `True`. The `--quiet` flag also suppresses the existing trailing "Next steps" advisory. → `src/kanon/cli.py` (`init` command). (depends: T1)
- [ ] T5: Add `--quiet` / `-q` flag to `kanon upgrade` and emit the banner via `click.echo(_BANNER, err=True)` when `_should_emit_banner(quiet)` is `True`. → `src/kanon/cli.py` (`upgrade` command). (depends: T1)
- [ ] T6: Add `test_banner_constant_used_by_all_surfaces` — assert `_BANNER` is referenced by `cli.py` (init + upgrade emission) and by `_scaffold.py::_assemble_agents_md`, with no other byte-equal copy in the source tree. Implements INV-kanon-banner-single-source. → `tests/test_cli.py`. (depends: T1, T3, T4, T5)
- [ ] T7: Add `test_banner_emitted_on_tty` and `test_banner_suppressed_when_stderr_not_tty` for both `init` and `upgrade`. Patch `sys.stderr.isatty` to return True/False. Implements INV-kanon-banner-tty-only. → `tests/test_cli.py`. (depends: T4, T5)
- [ ] T8: Add `test_banner_suppressed_with_quiet_flag` for both `init` and `upgrade`. Implements INV-kanon-banner-quiet-suppresses. → `tests/test_cli.py`. (depends: T4, T5)
- [ ] T9: Add `test_banner_goes_to_stderr_not_stdout` for both `init` and `upgrade`. Use `CliRunner(mix_stderr=False)` to verify. Implements INV-kanon-banner-stderr-only. → `tests/test_cli.py`. (depends: T4, T5)
- [ ] T10: Add `test_banner_exact_byte_content` (asserts `_BANNER` equals the literal) and `test_banner_present_at_top_of_scaffolded_agents_md` (asserts the bytes appear inside the banner marker block of a freshly scaffolded AGENTS.md). Implements INV-kanon-banner-byte-frozen. → `tests/test_cli.py`. (depends: T1, T3)
- [ ] T11: Add `test_banner_not_emitted_by_other_commands` (verify, aspect list, tier set, preflight, graph rename — none emit the banner) and `test_banner_in_agents_md_marker_block` (asserts the banner sits inside the marker pair, not loose prose). Implements INV-kanon-banner-surface-enumeration. → `tests/test_cli.py`. (depends: T3, T4, T5)
- [ ] T12: CHANGELOG `## [Unreleased]` entry under `### Added`: "kanon banner: shown on `init`/`upgrade` (TTY only, suppressed by `--quiet`) and at the top of scaffolded `AGENTS.md`." → `CHANGELOG.md`.
- [ ] T13: Run full `pytest` suite and `kanon verify .` against the worktree. Confirm `status: ok` and 0 new failures. → no file. (depends: T1-T12)

## Acceptance Criteria

- [ ] AC1 (INV-1): `_BANNER` is defined exactly once in `src/kanon/_banner.py`. `cli.py` and `_scaffold.py` both consume it by import; no other byte-equal copy exists in the source tree.
- [ ] AC2 (INV-2): `kanon init` emits `_BANNER` on stderr when `sys.stderr.isatty()` is `True`, and does not emit it when `False`. Same for `kanon upgrade`. The AGENTS.md surface is unaffected by TTY state (it's a file artifact).
- [ ] AC3 (INV-3): `kanon init --quiet` and `kanon upgrade --quiet` (and `-q`) suppress the banner regardless of TTY state. Exit codes and error output are unchanged.
- [ ] AC4 (INV-4): When `kanon init` and `kanon upgrade` emit the banner, it goes to stderr only — capturing stdout never includes the banner.
- [ ] AC5 (INV-5): The `_BANNER` constant equals an exact byte literal asserted by test. Scaffolded `AGENTS.md` contains those bytes verbatim inside the banner marker block.
- [ ] AC6 (INV-6): No CLI command other than `init` and `upgrade` emits the banner. The banner sits inside `<!-- kanon:begin:banner --> ... <!-- kanon:end:banner -->` markers in scaffolded AGENTS.md, not as loose prose.
- [ ] AC7: All 6 invariants in `docs/specs/kanon-banner.md` map to passing tests in `tests/test_cli.py` (per `invariant_coverage:` frontmatter).
- [ ] AC8: `kanon verify .` returns `status: ok`.
- [ ] AC9: `pytest` passes with no new failures.

## Documentation Impact

User-visible behavior change. Affected:
- `CHANGELOG.md` `## [Unreleased]` (T12).
- No README change — the banner is a visible-on-run experience, not a documented feature.
- No spec rewrites needed — the new banner spec is the documentation surface.
