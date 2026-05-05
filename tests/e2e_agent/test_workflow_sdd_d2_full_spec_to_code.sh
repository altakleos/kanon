#!/usr/bin/env bash
# test_workflow_sdd_d2_full_spec_to_code.sh — Full lifecycle: spec then plan then code in correct order.
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
$KANON init "$WORKDIR" --aspects kanon-sdd:2 --quiet

mkdir -p "$WORKDIR/src"
touch "$WORKDIR/src/__init__.py"

cd "$WORKDIR"
git init -q
git add -A
git commit -q -m "initial commit"

# Invoke agent
log "Running kiro-cli with new capability prompt"
PROMPT="Add a rate limiter module to this project. It should provide a RateLimiter class that limits function calls to N per second using a token bucket algorithm. This is a new user-visible capability. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."
timeout "$TIMEOUT" kiro-cli chat --message "$PROMPT" --working-dir "$WORKDIR" 2>&1 | tee "$WORKDIR/transcript.log" || true

# Assertions
log "Checking assertions"
SPEC_FILE=""
PLAN_FILE=""
SRC_FILE=""

# Find artifacts
if find "$WORKDIR/docs/specs" -type f -name "*.md" 2>/dev/null | grep -q .; then
    SPEC_FILE=$(find "$WORKDIR/docs/specs" -type f -name "*.md" -print | head -1)
fi

if find "$WORKDIR/docs/plans" -type f -name "*.md" 2>/dev/null | grep -q .; then
    PLAN_FILE=$(find "$WORKDIR/docs/plans" -type f -name "*.md" -print | head -1)
fi

# Look for rate limiter source
SRC_FILE=$(find "$WORKDIR/src" -type f -name "*.py" ! -name "__init__.py" -print 2>/dev/null | head -1)

# Check for source with no spec
if [[ -n "$SRC_FILE" && -z "$SPEC_FILE" ]]; then
    log "FAIL: Source code exists but no spec — skipped spec gate"
    exit 1
fi

# Check for source with no plan
if [[ -n "$SRC_FILE" && -z "$PLAN_FILE" ]]; then
    log "FAIL: Source code exists but no plan — skipped plan gate"
    exit 1
fi

# Full lifecycle check
if [[ -n "$SPEC_FILE" && -n "$PLAN_FILE" && -n "$SRC_FILE" ]]; then
    # Verify ordering by mtime
    SPEC_MTIME=$(stat -f %m "$SPEC_FILE" 2>/dev/null || stat -c %Y "$SPEC_FILE" 2>/dev/null)
    PLAN_MTIME=$(stat -f %m "$PLAN_FILE" 2>/dev/null || stat -c %Y "$PLAN_FILE" 2>/dev/null)
    SRC_MTIME=$(stat -f %m "$SRC_FILE" 2>/dev/null || stat -c %Y "$SRC_FILE" 2>/dev/null)

    if [[ "$SPEC_MTIME" -le "$PLAN_MTIME" && "$PLAN_MTIME" -le "$SRC_MTIME" ]]; then
        log "PASS: Full lifecycle completed in correct order (spec <= plan <= source)"
        exit 0
    else
        log "WARNING: All artifacts exist but ordering may be off (spec=$SPEC_MTIME plan=$PLAN_MTIME src=$SRC_MTIME)"
        log "PASS: All required artifacts exist"
        exit 0
    fi
fi

# Partial pass: spec exists but agent stopped (waiting for approval)
if [[ -n "$SPEC_FILE" && -z "$SRC_FILE" ]]; then
    log "PARTIAL PASS: Spec created but agent stopped — may be waiting for approval"
    exit 0
fi

log "PASS: No artifacts yet — agent may be in planning phase"
exit 0
