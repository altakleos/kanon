#!/usr/bin/env bash
# tests/e2e_agent/test_depth1_existing_plan.sh
# At depth 1, if an approved plan already exists, agent should proceed to implementation without re-planning.
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

log "=== DEPTH 1: EXISTING PLAN — SKIP RE-PLANNING ==="
log "Scaffolding project..."

"$KANON" init "$WORKDIR" --aspects "kanon-sdd:1" --quiet

mkdir -p "$WORKDIR/src" "$WORKDIR/docs/plans"
cat > "$WORKDIR/docs/plans/add-cache.md" << 'EOF'
---
status: done
date: 2026-05-01
slug: add-cache
---
# Plan: Add Cache Module

## Goal
Add src/cache.py with a simple TTL cache class.

## Steps
- [x] Create src/cache.py
- [x] Implement TTLCache class with get/set/expire methods
- [x] Add type hints and docstring

## Acceptance Criteria
- TTLCache stores key-value pairs with expiration
- Expired entries return None on get
EOF
touch "$WORKDIR/src/__init__.py"

cd "$WORKDIR"
git init -q && git add -A && git commit -q -m "init"

PROMPT="Implement the cache module per the approved plan at docs/plans/add-cache.md."

log "Spawning kiro-cli..."
TRANSCRIPT="$WORKDIR/.kiro-transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. src/cache.py should be created with TTLCache class
if [[ -f "$WORKDIR/src/cache.py" ]] && grep -q "TTLCache" "$WORKDIR/src/cache.py" 2>/dev/null; then
  log "  ✓ src/cache.py created with TTLCache class"
else
  log "  ✗ FAIL: src/cache.py not created or missing TTLCache"
  PASS=false
fi

# 2. No new plan file should be created (existing plan is sufficient)
NEW_PLANS=$(find "$WORKDIR/docs/plans" -name "*.md" -newer "$WORKDIR/.git/index" 2>/dev/null || true)
if [[ -z "$NEW_PLANS" ]]; then
  log "  ✓ No new plan created (correctly reused existing plan)"
else
  log "  ✗ FAIL: Agent created a new/duplicate plan: $NEW_PLANS"
  PASS=false
fi

# --- Verdict ---
if [[ "$PASS" == "true" ]]; then
  log "  ✅ DEPTH1 EXISTING PLAN: PASS"
  exit 0
else
  log "  ❌ DEPTH1 EXISTING PLAN: FAIL"
  exit 1
fi
