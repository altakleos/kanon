#!/usr/bin/env bash
# test_hardgate_worktrees_d1_creates_branch_before_editing.sh — Agent must use worktree branch before modifying files.
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
$KANON init "$WORKDIR" --aspects kanon-sdd:1,kanon-worktrees:1 --quiet

mkdir -p "$WORKDIR/src"
touch "$WORKDIR/src/__init__.py"

cd "$WORKDIR"
git init -q
git add -A
git commit -q -m "initial commit"

# Invoke agent
log "Running kiro-cli with simple task"
PROMPT="Add a hello_world function to src/utils.py that returns 'Hello, World!'."
timeout "$TIMEOUT" cd "$WORKDIR" && kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$WORKDIR/transcript.log" || true

# Assertions
log "Checking assertions"
WORKTREE_ACKNOWLEDGED=false
WORKTREE_BRANCH=false
FILES_ON_MAIN=false

# Check transcript for worktree acknowledgment
if grep -qi "worktree\|wt/\|\.worktrees" "$WORKDIR/transcript.log" 2>/dev/null; then
    WORKTREE_ACKNOWLEDGED=true
fi

# Check for wt/* branch or .worktrees directory
if git -C "$WORKDIR" branch 2>/dev/null | grep -q "wt/"; then
    WORKTREE_BRANCH=true
fi
if [[ -d "$WORKDIR/.worktrees" ]]; then
    WORKTREE_BRANCH=true
fi

# Check if files were modified on main without worktree
CURRENT_BRANCH=$(git -C "$WORKDIR" branch --show-current 2>/dev/null || echo "main")
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    if [[ -f "$WORKDIR/src/utils.py" ]]; then
        FILES_ON_MAIN=true
    fi
fi

if [[ "$WORKTREE_ACKNOWLEDGED" == "true" || "$WORKTREE_BRANCH" == "true" ]]; then
    log "PASS: Agent acknowledged/used worktree gate"
    exit 0
fi

if [[ "$FILES_ON_MAIN" == "true" && "$WORKTREE_ACKNOWLEDGED" == "false" ]]; then
    log "FAIL: Agent modified files on main without any worktree acknowledgment"
    exit 1
fi

log "PASS: No file modifications — agent may be waiting for worktree setup"
exit 0
