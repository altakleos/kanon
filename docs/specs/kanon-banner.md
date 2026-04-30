---
status: accepted (lite)
date: 2026-04-30
target-release: v0.3
realizes:
  - P-self-hosted-bootstrap
serves:
  - vision
stressed_by:
  - solo-engineer
fixtures:
  - tests/test_cli.py
invariant_coverage:
  INV-kanon-banner-single-source:
    - tests/test_cli.py::test_banner_constant_used_by_all_surfaces
  INV-kanon-banner-tty-only:
    - tests/test_cli.py::test_banner_emitted_on_tty
    - tests/test_cli.py::test_banner_suppressed_when_stderr_not_tty
  INV-kanon-banner-quiet-suppresses:
    - tests/test_cli.py::test_banner_suppressed_with_quiet_flag
  INV-kanon-banner-stderr-only:
    - tests/test_cli.py::test_banner_goes_to_stderr_not_stdout
  INV-kanon-banner-byte-frozen:
    - tests/test_cli.py::test_banner_exact_byte_content
    - tests/test_cli.py::test_banner_present_at_top_of_scaffolded_agents_md
  INV-kanon-banner-surface-enumeration:
    - tests/test_cli.py::test_banner_not_emitted_by_other_commands
    - tests/test_cli.py::test_banner_in_agents_md_marker_block
---
# Spec: `kanon` banner

## Intent

`kanon` deserves a small, distinctive visual identity at the moments it most clearly enters a user's workflow:

1. The first time `kanon init` scaffolds a project.
2. Each time `kanon upgrade` refreshes that scaffold.
3. Each new agent session that opens a kanon project (the agent reads `AGENTS.md` and sees the banner at the top).

The banner is purely cosmetic — it adds no information that affects behavior, and its absence must never break a workflow. It exists to make the first-run and session-open experience feel deliberate rather than utilitarian.

## Invariants

<!-- INV-kanon-banner-single-source -->
1. **Single source of truth.** The banner's byte content is defined by exactly one module-level constant (`_BANNER`) in `src/kanon/cli.py`. All three emission surfaces — `init` runtime output, `upgrade` runtime output, and the AGENTS.md scaffold template — consume that constant. No surface defines its own copy.

<!-- INV-kanon-banner-tty-only -->
2. **TTY-only emission (runtime surfaces).** The runtime surfaces (`init`, `upgrade`) emit the banner only when `sys.stderr.isatty()` returns `True`. When stderr is redirected to a file, piped to another process, or otherwise not a TTY, the banner is not emitted. This protects scripts, CI pipelines, and `--watch`-style tooling. Does not apply to the AGENTS.md surface — that's a file artifact, not stderr output.

<!-- INV-kanon-banner-quiet-suppresses -->
3. **`--quiet` honored (runtime surfaces).** When the user passes `--quiet` (or `-q`) to `init` or `upgrade`, the banner is suppressed regardless of TTY state. The flag suppresses *only* the banner and existing trailing advisory output; it does not suppress error messages or change exit codes.

<!-- INV-kanon-banner-stderr-only -->
4. **Stderr only (runtime surfaces).** Runtime emission writes to stderr, never stdout. Pipelines that capture `kanon init` or `kanon upgrade` stdout are unaffected.

<!-- INV-kanon-banner-byte-frozen -->
5. **Byte-frozen content.** The `_BANNER` constant is exact bytes — including the leading and trailing newlines — and is asserted equal to a literal in `tests/test_cli.py`. Changing the banner is a deliberate, reviewed, version-controlled act. The byte-frozen check covers all three surfaces: it tests the constant directly, asserts that `init` and `upgrade` emit it verbatim on stderr, and asserts that scaffolded `AGENTS.md` contains it byte-for-byte inside its marker block.

<!-- INV-kanon-banner-surface-enumeration -->
6. **Surface enumeration.** The banner appears at exactly three surfaces: `kanon init` stderr (gated by 2 and 3), `kanon upgrade` stderr (gated by 2 and 3), and the top of scaffolded `AGENTS.md` inside a `<!-- kanon:begin:banner --> ... <!-- kanon:end:banner -->` marker block above the `# AGENTS.md — kanon` heading. No other CLI command emits it. No other scaffolded file contains it. The `kanon` group help (no subcommand) does not emit it — Click's group help is the existing welcome surface there.

## Rationale

A single `_BANNER` constant feeding three surfaces is the cheapest way to keep the brand mark consistent. The byte-frozen invariant (5) makes drift impossible without a deliberate test update.

The marker block in AGENTS.md (`<!-- kanon:begin:banner -->`) is the same mechanism the kit already uses for other managed sections (`hard-gates`, `protocols-index`). It lets `kanon upgrade` refresh the banner if the constant ever changes, while leaving user-authored content outside the markers untouched. Placing the marker *above* the `# AGENTS.md — kanon` heading is intentional — visual identity reads first, then content.

`--quiet` is preferred over a `KANON_NO_BANNER` env var because Click's flag-based UX is consistent with every other suppression knob in the CLI. Future env-var suppression can be added without breaking this spec.

TTY detection on stderr (not stdout) is intentional. Some tools redirect stdout to capture output but leave stderr connected for human-visible messages — the banner belongs to that channel.

The AGENTS.md surface is harness-agnostic: every supported harness (Claude Code, Cursor, Codex, Windsurf, Copilot) either reads `AGENTS.md` directly or imports it via a shim. Putting the banner there means every new agent session opens with it without per-harness work.

## Out of Scope

- Color, ANSI escape codes, or terminal capability detection. The banner is plain ASCII; if a future change adds color, it gets its own spec amendment.
- Animated or progressive rendering. The banner is a single `click.echo` call.
- Configurable banner content (per-project, per-user). The banner is brand-level, not theming.
- Localization. The banner is not translated.
- A Claude Code `SessionStart` hook or other harness-specific runtime trigger. The AGENTS.md surface already covers every harness; per-harness hooks are out of scope.
- Banner in `CLAUDE.md` or other harness shims. They `@AGENTS.md`-import; the banner there would be redundant.
- Banner in `.kanon/kit.md` or other internal files. Not an agent-facing surface.

## Decisions

- No new ADR is required for this spec; it is a small UX addition fully described by these invariants.
- The chosen banner content is the figlet `standard` font rendering of `kanon`, captured byte-for-byte in `_BANNER`. Font choice is documented in the implementation plan; this spec does not constrain font, only that the bytes are frozen once chosen.
