#!/usr/bin/env bash
# tests/e2e_agent/test_trivial_skip.sh — Verify trivial changes skip the plan gate at depth 1.
#
# At depth 1, the plan-before-build gate's skip-when allows:
#   "fix a typo/spelling error, fix a single failing assertion without
#    changing logic, rename a local variable within one function, or
#    delete code proven unreachable by static analysis"
#
# This test gives kiro a trivial prompt (fix a typo) and asserts it
# proceeds WITHOUT writing a plan.
#
# Usage: ./tests/e2e_agent/test_trivial_skip.sh
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

log "=== TRIVIAL CHANGE AT DEPTH 1 ==="
log "Scaffolding project..."

"$KANON" init "$WORKDIR" --aspects "kanon-sdd:1" --quiet

# Create a file with a typo for the agent to fix
mkdir -p "$WORKDIR/src"
cat > "$WORKDIR/src/utils.py" << 'EOF'
def greet(name: str) -> str:
    """Retrun a greeting message."""
    return f"Hello, {name}!"
EOF

cd "$WORKDIR"
git init -q && git add -A && git commit -q -m "init"

PROMPT="Fix the typo in the docstring of src/utils.py — 'Retrun' should be 'Return'."

log "Spawning kiro-cli with trivial prompt..."
TRANSCRIPT="$WORKDIR/.kiro-transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. The typo should be fixed
if grep -q "Return a greeting" "$WORKDIR/src/utils.py" 2>/dev/null; then
  log "  ✓ Typo fixed in src/utils.py"
else
  log "  ✗ FAIL: Typo not fixed"
  PASS=false
fi

# 2. No plan should have been created (trivial change)
NEW_PLANS=$(find "$WORKDIR/docs/plans" -name "*.md" 2>/dev/null || true)
if [[ -z "$NEW_PLANS" ]]; then
  log "  ✓ No plan created (correctly skipped for trivial change)"
else
  log "  ✗ FAIL: Plan was created for a trivial typo fix: $NEW_PLANS"
  PASS=false
fi

# --- Verdict ---
if [[ "$PASS" == "true" ]]; then
  log "  ✅ TRIVIAL SKIP: PASS — agent fixed typo without unnecessary ceremony"
  exit 0
else
  log "  ❌ TRIVIAL SKIP: FAIL"
  log "  Transcript: $TRANSCRIPT"
  exit 1
fi
