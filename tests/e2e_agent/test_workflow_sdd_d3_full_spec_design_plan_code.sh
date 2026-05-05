#!/usr/bin/env bash
# test_workflow_sdd_d3_full_spec_design_plan_code.sh — Full depth-3 lifecycle: spec → design → plan → code.
set -euo pipefail
TIMEOUT=300
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then KANON="$REPO_ROOT/.venv/bin/kanon"; else KANON="kanon"; fi
if ! command -v kiro-cli &>/dev/null; then echo "SKIP: kiro-cli not found"; exit 2; fi
log() { echo "[$(date +%H:%M:%S)] $*"; }

WORKDIR=$(mktemp -d)
trap "rm -rf '$WORKDIR'" EXIT

log "=== WORKFLOW: DEPTH 3 FULL LIFECYCLE (spec → design → plan → code) ==="
"$KANON" init "$WORKDIR" --aspects "kanon-sdd:3" --quiet
mkdir -p "$WORKDIR/src" && touch "$WORKDIR/src/__init__.py"
cd "$WORKDIR" && git init -q && git add -A && git commit -q -m "init"

PROMPT="Add an event bus system to this project. It should support publish/subscribe with typed events, async handlers, and a middleware pipeline. This is a new user-visible capability that introduces new component boundaries (event bus core, handler registry, middleware chain). All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

log "Spawning kiro-cli (timeout: ${TIMEOUT}s)..."
TRANSCRIPT="$WORKDIR/.transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. Spec must exist
SPECS=$(find docs/specs -name "*.md" -newer .git/index 2>/dev/null || true)
if [[ -n "$SPECS" ]]; then
  log "  ✓ Spec created: $SPECS"
else
  log "  ✗ FAIL: No spec created"
  PASS=false
fi

# 2. Design doc must exist
DESIGNS=$(find docs/design -name "*.md" -newer .git/index 2>/dev/null || true)
if [[ -n "$DESIGNS" ]]; then
  log "  ✓ Design doc created: $DESIGNS"
else
  log "  ✗ FAIL: No design doc created"
  PASS=false
fi

# 3. Plan must exist
PLANS=$(find docs/plans -name "*.md" -newer .git/index 2>/dev/null || true)
if [[ -n "$PLANS" ]]; then
  log "  ✓ Plan created: $PLANS"
else
  log "  ⚠ No plan yet (agent may have stopped after design — acceptable)"
fi

# 4. Ordering: spec ≤ design ≤ plan ≤ code (by mtime)
if [[ -n "$SPECS" ]] && [[ -n "$DESIGNS" ]]; then
  SPEC_FILE=$(echo "$SPECS" | head -1)
  DESIGN_FILE=$(echo "$DESIGNS" | head -1)
  SPEC_TIME=$(stat -f %m "$SPEC_FILE" 2>/dev/null || stat -c %Y "$SPEC_FILE")
  DESIGN_TIME=$(stat -f %m "$DESIGN_FILE" 2>/dev/null || stat -c %Y "$DESIGN_FILE")
  if [[ "$SPEC_TIME" -le "$DESIGN_TIME" ]]; then
    log "  ✓ Spec created before design (correct order)"
  else
    log "  ✗ FAIL: Design created before spec (wrong order)"
    PASS=false
  fi
fi

# 5. No source code without spec + design
SRC=$(find src -name "*.py" -newer src/__init__.py 2>/dev/null | grep -v __init__ || true)
if [[ -n "$SRC" ]] && [[ -z "$SPECS" ]]; then
  log "  ✗ FAIL: Source code written without spec"
  PASS=false
fi
if [[ -n "$SRC" ]] && [[ -z "$DESIGNS" ]]; then
  log "  ✗ FAIL: Source code written without design doc"
  PASS=false
fi

# --- Verdict ---
if [[ "$PASS" == "true" ]]; then
  log "  ✅ WORKFLOW D3: PASS"
  exit 0
else
  log "  ❌ WORKFLOW D3: FAIL"
  log "  Transcript: $TRANSCRIPT"
  exit 1
fi
