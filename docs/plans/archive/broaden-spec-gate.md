---
status: done
design: "Follows existing check_process_gates.py pattern"
---

# Plan: Broaden spec gate to catch all Click registration patterns

## Problem

The spec co-presence gate in `check_process_gates.py` uses a regex that
matches `@cli.command(`, `@cli.group(`, and `@click.command(` — but the
actual codebase registers commands via `@main.command()`, `@aspect.command()`,
`@tier.command()`, `@fidelity.command()`, `@graph.command()`, and
`@click.group()`. The gate catches **none** of the real patterns.

## Changes

### 1. Broaden `_CLI_DECORATOR` regex

Replace the hardcoded group-name alternation with a general pattern that
matches any `@<identifier>.command(` or `@<identifier>.group(` in added
diff lines:

```python
_CLI_DECORATOR = re.compile(
    r"^\+.*@\w+\.(?:command|group)\("
)
```

This catches all current and future Click registration patterns regardless
of the group variable name.

### 2. Add tests for the broadened patterns

Add test cases for:
- `@main.command()` — currently the most common pattern (should trigger gate)
- `@aspect.command('list')` — subcommand with name arg (should trigger gate)
- `@click.group()` — top-level group (should trigger gate)

### 3. Update docstring

Update the script's docstring and error message to reflect the broader
detection.

## Acceptance criteria

- [x] `_CLI_DECORATOR` matches `@main.command(`, `@aspect.command(`, `@click.group(`, etc.
- [x] Existing tests still pass (backward compatible — old patterns still match)
- [x] New tests cover the previously-missed patterns
- [x] Script docstring updated
