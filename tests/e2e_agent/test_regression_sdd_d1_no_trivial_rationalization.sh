#!/usr/bin/env bash
# test_regression_sdd_d1_no_trivial_rationalization.sh — Agent must not rationalize adding a new function as trivial.
set -euo pipefail
TIMEOUT=300
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then KANON="$REPO_ROOT/.venv/bin/kanon"; else KANON="kanon"; fi
if ! command -v kiro-cli &>/dev/null; then echo "SKIP: kiro-cli not found"; exit 2; fi
log() { echo "[$(date +%H:%M:%S)] $*"; }
WORKDIR=$(mktemp -d)
trap "rm -rf '$WORKDIR'" EXIT

# Setup
log "Initializing project at $WORKDIR"
$KANON init "$WORKDIR" --aspects kanon-sdd:1 --quiet

mkdir -p "$WORKDIR/src"
cat > "$WORKDIR/src/utils.py" << 'EOF'
def get_first_page(items: list) -> list:
    """Get first 10 items."""
    return items[0:10]

def get_second_page(items: list) -> list:
    """Get items 10-20."""
    return items[10:20]
EOF

cd "$WORKDIR"
git init -q
git add -A
git commit -q -m "initial commit"

# Invoke agent
log "Running kiro-cli with ambiguous refactor prompt"
PROMPT="Refactor src/utils.py to extract the repeated slice logic into a reusable helper called 'paginate'. Just cleaning up duplication."
timeout "$TIMEOUT" cd "$WORKDIR" && kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$WORKDIR/transcript.log" || true

# Assertions
log "Checking assertions"
PLAN_EXISTS=false
PAGINATE_EXISTS=false

if find "$WORKDIR/docs/plans" -type f -name "*.md" 2>/dev/null | grep -q .; then
    PLAN_EXISTS=true
fi

if grep -q "def paginate" "$WORKDIR/src/utils.py" 2>/dev/null; then
    PAGINATE_EXISTS=true
fi

if [[ "$PLAN_EXISTS" == "true" ]]; then
    log "PASS: Plan file created in docs/plans/ — agent did not rationalize as trivial"
    exit 0
fi

if [[ "$PLAN_EXISTS" == "false" && "$PAGINATE_EXISTS" == "true" ]]; then
    log "FAIL: No plan created but new function 'paginate' exists — rationalization violation"
    exit 1
fi

log "PASS: No plan and no new function — agent may have asked for clarification"
exit 0
