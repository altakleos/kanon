#!/usr/bin/env bash
# tests/e2e_agent/test_depth3_design_required.sh
# At depth 3, introducing new component boundaries requires a design doc.
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

log "=== DEPTH 3: DESIGN DOC REQUIRED FOR NEW BOUNDARIES ==="
log "Scaffolding project..."

"$KANON" init "$WORKDIR" --aspects "kanon-sdd:3" --quiet

mkdir -p "$WORKDIR/docs/specs" "$WORKDIR/src"
cat > "$WORKDIR/docs/specs/plugin-system.md" << 'EOF'
---
status: accepted
date: 2026-05-01
slug: plugin-system
---
# Spec: Plugin System

## Summary
Add a plugin system with entry-point discovery, a PluginInterface ABC, and event dispatch.

## User-visible behavior
- Plugins register via entry points
- Core dispatches lifecycle events to plugins
- Plugin errors are isolated
EOF

cd "$WORKDIR"
git init -q && git add -A && git commit -q -m "init"

PROMPT="Implement the plugin system per the spec at docs/specs/plugin-system.md. This introduces new component boundaries: a plugin loader, a PluginInterface ABC, and an event dispatcher. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

log "Spawning kiro-cli..."
TRANSCRIPT="$WORKDIR/.kiro-transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. Design doc must be created (new component boundaries at depth 3)
NEW_DESIGN=$(find "$WORKDIR/docs/design" -name "*.md" -newer "$WORKDIR/.git/index" 2>/dev/null || true)
if [[ -n "$NEW_DESIGN" ]]; then
  log "  ✓ Design doc created: $NEW_DESIGN"
else
  log "  ✗ FAIL: No design doc in docs/design/ (required for new boundaries at depth 3)"
  PASS=false
fi

# 2. Source code should NOT exist without a design doc
NEW_SRC=$(find "$WORKDIR/src" -name "*.py" -newer "$WORKDIR/.git/index" 2>/dev/null | grep -v __init__ || true)
if [[ -n "$NEW_SRC" ]] && [[ -z "$NEW_DESIGN" ]]; then
  log "  ✗ FAIL: Code written without design doc (gate violation)"
  PASS=false
elif [[ -n "$NEW_SRC" ]] && [[ -n "$NEW_DESIGN" ]]; then
  log "  ✓ Code written after design doc (correct order)"
fi

# --- Verdict ---
if [[ "$PASS" == "true" ]]; then
  log "  ✅ DEPTH3 DESIGN REQUIRED: PASS"
  exit 0
else
  log "  ❌ DEPTH3 DESIGN REQUIRED: FAIL"
  exit 1
fi
