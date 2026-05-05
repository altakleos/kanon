#!/usr/bin/env bash
# tests/e2e_agent/helpers.sh — Shared helpers for E2E agent tests.
# Source this file: source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"

set -euo pipefail

# --- Environment ---
TIMEOUT="${TIMEOUT:-300}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then
  KANON="$REPO_ROOT/.venv/bin/kanon"
else
  KANON="kanon"
fi

# --- Prerequisites ---
require_kiro() {
  if ! command -v kiro-cli &>/dev/null; then
    echo "SKIP: kiro-cli not found"
    exit 2
  fi
}

# --- Logging ---
log() { echo "[$(date +%H:%M:%S)] $*"; }

# --- Project setup ---
# Creates a temp dir, scaffolds a kanon project, inits git.
# Usage: init_project DEPTH [EXTRA_ASPECTS]
#   init_project 2
#   init_project 1 ",kanon-worktrees:1"
# Sets: WORKDIR (exported for use in assertions)
init_project() {
  local depth=$1
  local extra="${2:-}"
  WORKDIR=$(mktemp -d)
  trap "rm -rf '$WORKDIR'" EXIT
  "$KANON" init "$WORKDIR" --aspects "kanon-sdd:${depth}${extra}" --quiet
  mkdir -p "$WORKDIR/src"
  touch "$WORKDIR/src/__init__.py"
  cd "$WORKDIR"
  git init -q && git add -A && git commit -q -m "init"
}

# --- Agent invocation ---
# Runs kiro-cli with a prompt in the current WORKDIR.
# Usage: run_agent "Add a paginate function..."
# Sets: TRANSCRIPT path
run_agent() {
  local prompt="$1"
  TRANSCRIPT="$WORKDIR/.transcript.log"
  log "Spawning kiro-cli (timeout: ${TIMEOUT}s)..."
  timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$prompt" \
    2>&1 | tee "$TRANSCRIPT" || true
}

# --- Assertions ---
# All assertion helpers exclude scaffolded templates (_template.md, README.md).

# Check if agent-created files exist in a docs/ subdirectory.
# Usage: has_new_docs "specs"  → true if docs/specs/ has non-template .md files
has_new_docs() {
  local subdir="$1"
  find "$WORKDIR/docs/$subdir" -type f -name "*.md" \
    ! -name "_template.md" ! -name "README.md" 2>/dev/null | grep -q .
}

# Check if agent created source files (excluding __init__.py).
# Usage: has_new_source
has_new_source() {
  find "$WORKDIR/src" -type f -name "*.py" ! -name "__init__.py" 2>/dev/null | grep -q .
}

# Check if transcript contains a pattern (case-insensitive).
# Usage: transcript_contains "vision"
transcript_contains() {
  grep -qi "$1" "$TRANSCRIPT" 2>/dev/null
}

# Check if transcript does NOT contain a pattern.
# Usage: transcript_lacks "populate foundations"
transcript_lacks() {
  ! grep -qi "$1" "$TRANSCRIPT" 2>/dev/null
}

# Assert and log. Usage: assert "description" CONDITION
# Example: assert "Plan created" has_new_docs plans
assert_pass() {
  local desc="$1"
  shift
  if "$@"; then
    log "  ✓ $desc"
    return 0
  else
    log "  ✗ FAIL: $desc"
    return 1
  fi
}

assert_fail() {
  local desc="$1"
  shift
  if "$@"; then
    log "  ✗ FAIL: $desc (should NOT exist)"
    return 1
  else
    log "  ✓ $desc (correctly absent)"
    return 0
  fi
}

# --- Verdict ---
# Call at end of test. Tracks PASS state.
PASS=true

fail() {
  PASS=false
}

verdict() {
  local label="${1:-TEST}"
  if [[ "$PASS" == "true" ]]; then
    log "  ✅ $label: PASS"
    exit 0
  else
    log "  ❌ $label: FAIL"
    log "  Transcript: $TRANSCRIPT"
    exit 1
  fi
}
