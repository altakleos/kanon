#!/usr/bin/env bash
# tests/e2e_agent/test_depth3_skip_design.sh
# At depth 3, a change following an existing pattern (no new boundaries) should skip the design gate.
#
# Exit codes: 0=PASS, 1=FAIL, 2=SKIP
set -euo pipefail

TIMEOUT=300
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then KANON="$REPO_ROOT/.venv/bin/kanon"; else KANON="kanon"; fi
if ! command -v kiro-cli &>/dev/null; then echo "SKIP: kiro-cli not found"; exit 2; fi
log() { echo "[$(date +%H:%M:%S)] $*"; }

WORKDIR=$(mktemp -d)
trap "rm -rf '$WORKDIR'" EXIT

log "=== DEPTH 3: SKIP DESIGN FOR EXISTING PATTERN ==="
log "Scaffolding project..."

"$KANON" init "$WORKDIR" --aspects "kanon-sdd:3" --quiet

mkdir -p "$WORKDIR/docs/specs" "$WORKDIR/docs/design" "$WORKDIR/src/cli"
cat > "$WORKDIR/docs/specs/status-command.md" << 'EOF'
---
status: accepted
date: 2026-05-01
slug: status-command
---
# Spec: Status Command

## Summary
Add `kanon status` that prints current depth and active aspects.

## User-visible behavior
- Prints depth and aspect list to stdout
- Exit code 0
EOF

cat > "$WORKDIR/docs/design/cli-architecture.md" << 'EOF'
---
status: accepted
---
# Design: CLI Architecture

## Components
- CLI entry point (click group)
- Command modules (one file per command in src/cli/)

## Pattern
Each command is a @click.command() function in src/cli/<name>.py
EOF

cat > "$WORKDIR/src/cli/__init__.py" << 'EOF'
"""CLI package."""
EOF

cat > "$WORKDIR/src/cli/verify.py" << 'EOF'
# src/cli/verify.py
import click
@click.command()
def verify():
    """Verify project."""
    click.echo("OK")
EOF

cd "$WORKDIR"
git init -q && git add -A && git commit -q -m "init"

PROMPT="Implement the status command per docs/specs/status-command.md. Follow the existing CLI pattern in docs/design/cli-architecture.md — add a new file src/cli/status.py. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

log "Spawning kiro-cli..."
TRANSCRIPT="$WORKDIR/.kiro-transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. No new design doc should be created (follows existing pattern)
NEW_DESIGN=$(find "$WORKDIR/docs/design" -name "*.md" -newer "$WORKDIR/.git/index" 2>/dev/null | grep -v cli-architecture || true)
if [[ -z "$NEW_DESIGN" ]]; then
  log "  ✓ No new design doc created (correctly follows existing pattern)"
else
  log "  ✗ FAIL: Unnecessary design doc created: $NEW_DESIGN"
  PASS=false
fi

# 2. src/cli/status.py should be created (implementation happened)
if [[ -f "$WORKDIR/src/cli/status.py" ]]; then
  log "  ✓ src/cli/status.py created"
else
  log "  ✗ FAIL: src/cli/status.py not created"
  PASS=false
fi

# --- Verdict ---
if [[ "$PASS" == "true" ]]; then
  log "  ✅ DEPTH3 SKIP DESIGN: PASS"
  exit 0
else
  log "  ❌ DEPTH3 SKIP DESIGN: FAIL"
  exit 1
fi
