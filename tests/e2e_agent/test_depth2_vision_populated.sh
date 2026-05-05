#!/usr/bin/env bash
# tests/e2e_agent/test_depth2_vision_populated.sh
# At depth 2 with pre-populated vision.md, agent should NOT offer to write foundations.
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

log "=== DEPTH 2: VISION POPULATED — NO FOUNDATIONS OFFER ==="
log "Scaffolding project..."

"$KANON" init "$WORKDIR" --aspects "kanon-sdd:2" --quiet

mkdir -p "$WORKDIR/src" "$WORKDIR/docs/foundations"
cat > "$WORKDIR/docs/foundations/vision.md" << 'EOF'
---
status: accepted
---
# Vision

## Mission
A CLI tool for managing development workflows.

## Non-goals
- Not a build system
- Not a CI/CD replacement

## Key bets
- Convention over configuration
- Graduated complexity
EOF
touch "$WORKDIR/src/__init__.py"

cd "$WORKDIR"
git init -q && git add -A && git commit -q -m "init"

PROMPT="Add a new 'export' command that exports the project configuration as YAML to stdout. This is a new user-visible capability."

log "Spawning kiro-cli..."
TRANSCRIPT="$WORKDIR/.kiro-transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. Spec should be created (depth 2 + new user-visible capability)
NEW_SPECS=$(find "$WORKDIR/docs/specs" -name "*.md" -newer "$WORKDIR/.git/index" 2>/dev/null || true)
if [[ -n "$NEW_SPECS" ]]; then
  log "  ✓ Spec created: $NEW_SPECS"
else
  log "  ✗ FAIL: No spec created for new user-visible capability"
  PASS=false
fi

# 2. Transcript should NOT mention writing/populating foundations
if grep -qiE "(foundations are empty|populate foundations|write a vision)" "$TRANSCRIPT" 2>/dev/null; then
  log "  ✗ FAIL: Agent offered to write foundations despite vision.md existing"
  PASS=false
else
  log "  ✓ Agent did not offer to write foundations (correct — already populated)"
fi

# --- Verdict ---
if [[ "$PASS" == "true" ]]; then
  log "  ✅ DEPTH2 VISION POPULATED: PASS"
  exit 0
else
  log "  ❌ DEPTH2 VISION POPULATED: FAIL"
  exit 1
fi
