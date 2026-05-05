#!/usr/bin/env bash
# tests/e2e_agent/test_depth2_refactor_skip_spec.sh
# At depth 2, an internal refactor (no new user-visible capability) should skip the spec gate.
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

log "=== DEPTH 2: REFACTOR SKIPS SPEC ==="
log "Scaffolding project..."

"$KANON" init "$WORKDIR" --aspects "kanon-sdd:2" --quiet

mkdir -p "$WORKDIR/src"
cat > "$WORKDIR/src/utils.py" << 'EOF'
def process(data: dict) -> dict:
    """Process input data."""
    if not isinstance(data, dict):
        raise TypeError("Expected dict")
    if "name" not in data:
        raise ValueError("Missing name")
    if len(data["name"]) > 100:
        raise ValueError("Name too long")
    return {"greeting": f"Hello, {data['name']}!", "status": "ok"}
EOF

cd "$WORKDIR"
git init -q && git add -A && git commit -q -m "init"

PROMPT="Refactor src/utils.py: extract the validation logic from the 'process' function into a private helper '_validate_input'. No behavior change — same inputs produce same outputs."

log "Spawning kiro-cli..."
TRANSCRIPT="$WORKDIR/.kiro-transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. No spec should be created (refactor = no new user-visible capability)
NEW_SPECS=$(find "$WORKDIR/docs/specs" -name "*.md" 2>/dev/null || true)
if [[ -z "$NEW_SPECS" ]]; then
  log "  ✓ No spec created (correctly skipped for internal refactor)"
else
  log "  ✗ FAIL: Spec created for a pure internal refactor: $NEW_SPECS"
  PASS=false
fi

# 2. src/utils.py should be modified (refactor happened)
if grep -q "_validate_input" "$WORKDIR/src/utils.py" 2>/dev/null; then
  log "  ✓ src/utils.py refactored (_validate_input exists)"
else
  log "  ✗ FAIL: src/utils.py not refactored (no _validate_input found)"
  PASS=false
fi

# --- Verdict ---
if [[ "$PASS" == "true" ]]; then
  log "  ✅ DEPTH2 REFACTOR SKIP SPEC: PASS"
  exit 0
else
  log "  ❌ DEPTH2 REFACTOR SKIP SPEC: FAIL"
  exit 1
fi
