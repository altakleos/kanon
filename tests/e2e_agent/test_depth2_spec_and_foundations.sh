#!/usr/bin/env bash
# tests/e2e_agent/test_depth2_spec_and_foundations.sh
#
# At depth 2, the agent must:
#   1. Write a spec (docs/specs/*.md) before planning/building
#   2. Recommend/offer foundation docs (vision.md) via the foundations-authoring protocol
#
# Usage: ./tests/e2e_agent/test_depth2_spec_and_foundations.sh
#
# Exit codes: 0=PASS, 1=FAIL, 2=SKIP

set -euo pipefail

TIMEOUT=300
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then
  KANON="$REPO_ROOT/.venv/bin/kanon"
else
  KANON="kanon"
fi

if ! command -v kiro-cli &>/dev/null; then
  echo "SKIP: kiro-cli not found"; exit 2
fi

log() { echo "[$(date +%H:%M:%S)] $*"; }

WORKDIR=$(mktemp -d)
trap "rm -rf '$WORKDIR'" EXIT

log "=== DEPTH 2: SPEC + FOUNDATIONS ==="
log "Scaffolding project..."

"$KANON" init "$WORKDIR" --aspects "kanon-sdd:2" --quiet

# Create minimal src structure
mkdir -p "$WORKDIR/src"
touch "$WORKDIR/src/__init__.py"

cd "$WORKDIR"
git init -q && git add -A && git commit -q -m "init"

PROMPT="Add a new user authentication system to this project. It should support email/password login and JWT tokens. This is a new user-visible capability."

log "Spawning kiro-cli (timeout: ${TIMEOUT}s)..."
TRANSCRIPT="$WORKDIR/.kiro-transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. Spec file must be created (depth 2 requires spec before design/plan)
NEW_SPECS=$(find "$WORKDIR/docs/specs" -name "*.md" -newer "$WORKDIR/.git/index" 2>/dev/null || true)
if [[ -n "$NEW_SPECS" ]]; then
  log "  ✓ Spec file created: $NEW_SPECS"
else
  log "  ✗ FAIL: No spec file created in docs/specs/"
  PASS=false
fi

# 2. Agent should mention or offer foundation docs (vision.md)
#    The foundations-authoring protocol fires at depth 2 when vision.md is a template.
#    We check the transcript for any mention of "vision", "foundation", or the protocol name.
if grep -qiE "(vision|foundation|foundations-authoring)" "$TRANSCRIPT" 2>/dev/null; then
  log "  ✓ Foundations/vision mentioned in transcript"
else
  log "  ⚠ Foundations/vision not mentioned (soft protocol — not a hard failure)"
fi

# 3. Plan should also be created (depth 2 includes depth 1 gates)
NEW_PLANS=$(find "$WORKDIR/docs/plans" -name "*.md" -newer "$WORKDIR/.git/index" 2>/dev/null || true)
if [[ -n "$NEW_PLANS" ]]; then
  log "  ✓ Plan file also created: $NEW_PLANS"
else
  log "  ⚠ No plan file (agent may still be in spec phase — acceptable)"
fi

# 4. No source code should exist before spec (if source exists, spec must too)
NEW_SRC=$(find "$WORKDIR/src" -name "*.py" -newer "$WORKDIR/src/__init__.py" 2>/dev/null | grep -v __init__ || true)
if [[ -n "$NEW_SRC" ]] && [[ -z "$NEW_SPECS" ]]; then
  log "  ✗ FAIL: Source code written WITHOUT a spec (gate violation!)"
  PASS=false
fi

# --- Verdict ---
if [[ "$PASS" == "true" ]]; then
  log "  ✅ DEPTH 2: PASS"
  exit 0
else
  log "  ❌ DEPTH 2: FAIL"
  log "  Transcript: $TRANSCRIPT"
  exit 1
fi
