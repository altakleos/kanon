---
status: accepted
implements: docs/specs/preflight.md
date: 2026-04-28
---
# Design: `kanon preflight` — staged local validation

> **Phase A.4 supersession note** (2026-05-02, plan v040a1-followup): The
> `${test_cmd}` / `${lint_cmd}` / `${typecheck_cmd}` / `${format_cmd}` config-
> schema placeholders described in §"Aspect contributions" and §"Empty command
> handling" below were retired in Phase A.4 (PR #66) per ADR-0048 de-opinionation
> — the substrate no longer ships kanon-testing's `config-schema:` block, and
> the kanon-testing aspect's depth-1 `preflight:` block (which referenced these
> placeholders) was deleted with them. Today's preflight model: consumers wire
> their preflight commands directly under `.kanon/config.yaml`'s
> `preflight-stages:` block; aspect-contributed defaults survive only for
> aspects that author them with concrete commands (e.g., kanon-deps depth-2's
> push stage that runs `python scripts/check_deps.py`). The pipeline + merge
> semantics described in §"Check resolution pipeline" / §"Merge semantics" /
> §"CLI implementation" are still accurate. The historical body below is
> preserved for traceability of how preflight was conceived.

## Context

`kanon verify` is structural-only (INV-9). Consumers need a single
command that runs lint, tests, typecheck, and verify before pushing —
catching CI failures locally. The preflight command fills this gap
without contaminating verify's contract.

## Architecture

### Command surface

```
kanon preflight <target> [--stage commit|push|release] [--tag TAG] [--fail-fast]
```

Default stage: `commit`. Target is a path to the project root.

### Check resolution pipeline

```
1. Load .kanon/config.yaml → aspects + preflight-stages
2. Collect aspect-contributed defaults:
   for each (aspect, depth) in enabled_aspects:
     sub = load_aspect_manifest(aspect)
     for d in range(min_depth, depth + 1):
       for stage, checks in sub[depth-d].get("preflight", {}).items():
         aspect_defaults[stage].extend(checks)
3. Merge with consumer overrides:
   for stage in [commit, push, release]:
     resolved[stage] = consumer_stages.get(stage, aspect_defaults[stage])
     # Consumer entries override by label, append if new label
4. Build the run list for the requested stage:
   run_list = []
   for s in [commit, push, release]:
     run_list.extend(resolved[s])
     if s == requested_stage:
       break
5. Prepend kanon verify as the first check (always)
6. Execute run_list sequentially, collect results
```

### Merge semantics (aspect defaults + consumer overrides)

Aspect defaults are collected from all enabled aspects, sorted by
aspect name for determinism. Consumer `preflight-stages:` entries
in config.yaml take precedence:

- **Same label**: consumer entry replaces the aspect default.
- **New label**: consumer entry is appended after aspect defaults.
- **No consumer entry for a stage**: aspect defaults used as-is.

This means a consumer can override `tests` (change the command) or
add `custom-check` (extend the stage) without touching aspect manifests.

### Config schema

**In `.kanon/config.yaml` (consumer-authored):**

```yaml
preflight-stages:
  commit:
    - run: ruff check .
      label: lint
    - run: ruff format --check .
      label: format
  push:
    - run: pytest -q
      label: tests
    - run: mypy src/
      label: typecheck
  release:
    - run: python scripts/release-preflight.py --tag $TAG
      label: release-preflight
```

**In aspect sub-manifest (kit-authored):**

```yaml
# kanon-testing/manifest.yaml
depth-1:
  preflight:
    commit:
      - run: ${lint_cmd}
        label: lint
      - run: ${format_cmd}
        label: format
    push:
      - run: ${test_cmd}
        label: tests
      - run: ${typecheck_cmd}
        label: typecheck
```

The `${lint_cmd}` placeholders resolve from the aspect's config
values. If a config value is empty string, the check is skipped
(not an error — the consumer hasn't configured that tool).

### Testing aspect config-schema additions

```yaml
# Added to kanon-testing/manifest.yaml config-schema
config-schema:
  coverage_floor:
    type: integer
    default: 80
    description: ...existing...
  test_cmd:
    type: string
    default: ""
    description: "Test suite command (e.g., pytest -q, npm test)"
  lint_cmd:
    type: string
    default: ""
    description: "Lint command (e.g., ruff check ., eslint .)"
  typecheck_cmd:
    type: string
    default: ""
    description: "Type check command (e.g., mypy src/, tsc --noEmit)"
  format_cmd:
    type: string
    default: ""
    description: "Format check command (e.g., ruff format --check .)"
```

### Security aspect contribution

```yaml
# kanon-security/manifest.yaml
depth-2:
  preflight:
    push:
      - run: python scripts/check_security_patterns.py .
        label: security-scan
```

### Release aspect contribution

```yaml
# kanon-release/manifest.yaml
depth-2:
  preflight:
    release:
      - run: python scripts/release-preflight.py --tag $TAG
        label: release-preflight
```

### CLI implementation

New Click command in `cli.py`:

```python
@main.command()
@click.argument("target", type=click.Path(...))
@click.option("--stage", type=click.Choice(["commit", "push", "release"]),
              default="commit")
@click.option("--tag", default=None)
@click.option("--fail-fast", is_flag=True)
def preflight(target, stage, tag, fail_fast):
    # 1. Run kanon verify
    # 2. Resolve checks for requested stage
    # 3. Execute each check via subprocess.run(cmd, shell=True)
    # 4. Collect results, emit JSON summary
```

The command lives alongside `verify` in cli.py. It imports
`_read_config`, `_config_aspects`, and the new
`_resolve_preflight_checks()` function from `_scaffold.py` (or a
new `_preflight.py` module).

### Output format

**stderr** (human-readable, streaming):
```
✓ verify (structural)                    0.8s
✓ lint: ruff check .                     1.2s
✓ format: ruff format --check .          0.3s
✗ tests: pytest -q                       12.4s
── push: 3 of 4 checks passed ──
```

**stdout** (JSON, for CI consumption):
```json
{
  "stage": "push",
  "checks": [
    {"label": "verify", "command": "kanon verify .", "passed": true, "duration_s": 0.8},
    {"label": "lint", "command": "ruff check .", "passed": true, "duration_s": 1.2},
    {"label": "format", "command": "ruff format --check .", "passed": true, "duration_s": 0.3},
    {"label": "tests", "command": "pytest -q", "passed": false, "duration_s": 12.4}
  ],
  "passed": false
}
```

### Subprocess execution

Each check runs via `subprocess.run(cmd, shell=True, cwd=target)`.
Environment variables:
- `$TAG` — set from `--tag` flag (release stage only)
- Inherits the parent process environment

Trust boundary: commands come from `.kanon/config.yaml` (consumer-
authored, same trust as Makefile) or aspect manifests (kit-authored).
Both are committed files under the consumer's control.

### Empty command handling

If a `${test_cmd}` placeholder resolves to empty string (consumer
hasn't configured the tool), the check is **skipped** with a note
in the output: `⊘ tests: (not configured)`. Not an error — the
consumer may not use that tool category.

## Interaction with existing commands

- **`kanon verify`**: Unchanged. Preflight calls it as step 1.
- **`kanon upgrade`**: No change. Preflight config is consumer-authored.
- **`kanon init --profile standard`**: Could set default `*_cmd`
  values based on detected project type. Deferred — start with
  empty defaults, let the consumer configure.

## Alternatives considered

| Alternative | Why rejected |
|------------|-------------|
| Extend `kanon verify` with `--stage` | Violates INV-9; muddies verify's clean semantics |
| New `kanon-preflight` aspect | "Run checks" is not a discipline; it's a CLI command |
| Merge testing + release into `quality` | One depth dial can't serve two axes (methodology + ceremony) |
| Git hook auto-installation | Vision non-goal: no runtime enforcement hooks |

## Risks

1. **Shell injection from config commands.** Mitigated: config is
   consumer-authored (same trust as Makefile). Document the trust
   boundary.
2. **Slow preflight kills adoption.** Mitigated: commit stage is
   fast (<10s); push stage is the thorough one. `--fail-fast` for
   impatient developers.
3. **Aspect manifest `preflight:` key adds schema complexity.**
   Mitigated: optional key, ignored if absent. Existing manifests
   work unchanged.
