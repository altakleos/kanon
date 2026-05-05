#!/usr/bin/env bash
# test_hardgate_sdd_d3_skips_design_for_pattern.sh — D3: existing pattern skips design.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 3
mkdir -p docs/specs docs/design src/cli

echo -e "# Spec: Status Command\n**Status:** accepted\n## Requirements\n- Shows SDD depth and aspects" > docs/specs/status-command.md
echo -e "# Design: CLI Architecture\nEach command lives in src/cli/. Commands use Click." > docs/design/cli-architecture.md
echo -e "import click\n@click.group()\ndef main(): pass" > src/cli/__init__.py
echo -e "import click\nfrom src.cli import main\n@main.command()\ndef verify():\n    click.echo('OK')" > src/cli/verify.py
git add -A && git commit -q -m "add cli pattern"

DESIGN_COUNT=$(find docs/design -type f -name "*.md" ! -name "_template.md" ! -name "README.md" | wc -l)

run_agent "Implement the status command per docs/specs/status-command.md. Follow the existing CLI pattern in docs/design/cli-architecture.md — add a new file src/cli/status.py. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

NEW_DESIGN_COUNT=$(find docs/design -type f -name "*.md" ! -name "_template.md" ! -name "README.md" | wc -l)
if [[ "$NEW_DESIGN_COUNT" -gt "$DESIGN_COUNT" ]]; then
  log "  ✗ FAIL: New design doc created (should reuse existing pattern)"
  fail
else
  log "  ✓ No new design doc"
fi

verdict "D3_SKIPS_DESIGN_FOR_PATTERN"
