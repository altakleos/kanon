---
status: accepted
date: 2026-04-30
implements: docs/specs/kanon-banner.md
---
# Design: `kanon` banner

## Context

The `kanon-banner` spec requires a single `_BANNER` constant whose bytes appear at three surfaces (`init` stderr, `upgrade` stderr, top of scaffolded `AGENTS.md` inside a marker block) without any second copy. This design pins the *mechanism* by which the bytes reach each surface, and confirms the existing AGENTS.md scaffolding code already supports the chosen approach.

## Architecture

### Single source

```
src/kanon/cli.py
  └─ _BANNER: str  ──────────────┐
                                 │
                          consumed by:
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
  init runtime         upgrade runtime         AGENTS.md scaffold
  click.echo(_BANNER,  click.echo(_BANNER,    _replace_section(
    err=True) if         err=True) if           text, "banner",
    _should_emit()       _should_emit()         _BANNER)
```

`_should_emit()` returns `True` when stderr is a TTY *and* `--quiet` was not passed; `False` otherwise. Lives next to `_BANNER` in `cli.py`.

### Surface 3: AGENTS.md (template substitution, option 3)

The base template at `src/kanon/kit/agents-md-base.md` gains an *empty* marker block at the very top:

```markdown
<!-- kanon:begin:banner -->
<!-- kanon:end:banner -->
# AGENTS.md — ${project_name}

...
```

`_assemble_agents_md` already loops through known marker sections (`hard-gates`, `protocols-index`) and fills each via `_replace_section(text, name, content)`. We extend the function with one additional call:

```python
text = _replace_section(text, "banner", _BANNER)
```

The existing `_replace_section` / `_find_section_pair` machinery is position-agnostic — it locates marker pairs by string scan, not by document structure — so a marker block *above* the H1 is handled identically to one in the body. Confirmed by reading `_scaffold.py`:

- `_find_section_pair` returns the first occurrence of `<!-- kanon:begin:<name> -->` / `<!-- kanon:end:<name> -->`.
- `_replace_section` slices around the marker pair and substitutes.
- Neither references the H1.

No rewriter changes needed.

### Upgrade refresh

`kanon upgrade` already calls `_assemble_agents_md(aspects, target.name)` and writes the result through the AGENTS.md merger (which preserves user content outside marker blocks). When `_BANNER` changes between kit versions, the next `upgrade` rewrites the banner marker block automatically — same mechanism that already refreshes `hard-gates` and `protocols-index`. No special-case code.

## Interfaces

**New module-level surface (`src/kanon/cli.py`):**

```python
_BANNER: str = """
  _  __                       
 | |/ /__ _ _ __   ___  _ __  
 | ' // _` | '_ \\ / _ \\| '_ \\ 
 | . \\ (_| | | | | (_) | | | |
 |_|\\_\\__,_|_| |_|\\___/|_| |_|
                              
"""

def _should_emit_banner(quiet: bool) -> bool:
    return (not quiet) and sys.stderr.isatty()
```

**Touched modules:**

- `src/kanon/cli.py` — define `_BANNER`, define `_should_emit_banner`, add `--quiet/-q` flag to `init` and `upgrade`, emit banner before existing output when `_should_emit_banner` returns `True`.
- `src/kanon/_scaffold.py::_assemble_agents_md` — add `_replace_section(text, "banner", _BANNER)` call. Imports `_BANNER` from `cli` (acceptable circular-free direction since `cli` already imports from `_scaffold`, not vice versa — so import goes through a small intermediate or the constant is duplicated…). **Resolution:** move `_BANNER` to a new tiny module `src/kanon/_banner.py` to avoid the circular import. Both `cli.py` and `_scaffold.py` import it. Single source preserved.
- `src/kanon/kit/agents-md-base.md` — add empty `<!-- kanon:begin:banner --> <!-- kanon:end:banner -->` pair above the H1.

**No changes** to `_replace_section`, `_find_section_pair`, or the AGENTS.md merger.

**CLI surface added:**

- `kanon init [--quiet | -q]`
- `kanon upgrade [--quiet | -q]`

`--quiet` is also wired to suppress the existing trailing "Next steps" advisory on `init` (per spec invariant 3 — "suppresses *only* the banner and existing trailing advisory output").

## Decisions

- **Option 3 (template substitution) chosen** over option 1 (template-static) because it preserves spec invariant 1 (single source of truth), and over option 2 (runtime-injection prepending) because it reuses the existing marker-replacement machinery without introducing a parallel "prepend before assembly" code path.
- **Banner constant lives in `src/kanon/_banner.py`** (new tiny module) rather than `cli.py`, to keep the import graph clean — `_scaffold.py` cannot import from `cli.py` without inducing a cycle.
- **No rewriter changes.** The existing position-agnostic marker scan handles the above-H1 case. Verified by reading `_find_section_pair` — purely string-based, no structural assumptions.
- **`--quiet` flag** is the suppression knob; no `KANON_NO_BANNER` env var. Aligns with Click conventions used elsewhere in the CLI. Future env-var support is non-breaking and out of scope.
