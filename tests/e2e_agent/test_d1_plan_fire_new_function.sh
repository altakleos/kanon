#!/usr/bin/env bash
# test_d1_plan_fire_new_function.sh — Depth 1: adding a function requires a plan.
set -euo pipefail
TIMEOUT=300
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then KANON="$REPO_ROOT/.venv/bin/kanon"; else KANON="kanon"; fi
if ! command -v kiro-cli &>/dev/null; then echo "SKIP: kiro-cli not found"; exit 2; fi
log() { echo "[$(date +%H:%M:%S)] $*"; }

WORKDIR=$(mktemp -d)
trap "rm -rf '$WORKDIR'" EXIT

log "=== DEPTH 1: PLAN REQUIRED FOR NEW FUNCTION ==="
"$KANON" init "$WORKDIR" --aspects "kanon-sdd:1" --quiet
mkdir -p "$WORKDIR/src" && touch "$WORKDIR/src/__init__.py"
cd "$WORKDIR" && git init -q && git add -A && git commit -q -m "init"

PROMPT="Add a function called 'paginate' to src/utils.py that takes a list, page number, and page size, and returns the appropriate slice. Include type hints and a docstring."
log "Spawning kiro-cli..."
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee .transcript.log || true

PASS=true

# Plan must be created
NEW_PLANS=$(find docs/plans -name "*.md" -newer .git/index 2>/dev/null || true)
if [[ -n "$NEW_PLANS" ]]; then
  log "  ✓ Plan file created: $NEW_PLANS"
else
  log "  ✗ FAIL: No plan file created"
  PASS=false
fi

# Source without plan = violation
NEW_SRC=$(find src -name "*.py" -newer src/__init__.py 2>/dev/null | grep -v __init__ || true)
if [[ -n "$NEW_SRC" ]] && [[ -z "$NEW_PLANS" ]]; then
  log "  ✗ FAIL: Source code written WITHOUT a plan (gate violation!)"
  PASS=false
fi

if [[ "$PASS" == "true" ]]; then log "  ✅ PASS"; exit 0; else log "  ❌ FAIL"; exit 1; fi
