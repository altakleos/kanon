#!/usr/bin/env bash
# tests/e2e_agent/test_sdd_gates.sh — Live LLM E2E test for kanon SDD gates.
#
# Spawns kiro-cli against a scaffolded project at each SDD depth and verifies
# the agent respects the graduated ceremony:
#   Depth 0: Agent writes code directly (no plan/spec/design)
#   Depth 1: Agent writes a plan before code
#   Depth 2: Agent writes a spec before planning
#   Depth 3: Agent writes a design doc before spec
#
# Usage:
#   ./tests/e2e_agent/test_sdd_gates.sh [DEPTH]
#   DEPTH defaults to 1 (most valuable single test).
#   Set DEPTH=all to run all 4 depths.
#
# Requirements:
#   - kiro-cli installed and on PATH
#   - kanon installed and on PATH
#   - Active Midway session (for kiro-cli)
#
# Exit codes:
#   0 = PASS (agent respected gates at the tested depth)
#   1 = FAIL (gate violation detected)
#   2 = SKIP (prerequisites not met)

set -euo pipefail

# --- Config ---
TIMEOUT=300  # 5 minutes max per depth
PROMPT="Add a function called 'paginate' to src/utils.py that takes a list, page number, and page size, and returns the appropriate slice. Include type hints and a docstring."
# Use the dev venv's kanon if available (picks up unreleased protocol changes)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then
  KANON="$REPO_ROOT/.venv/bin/kanon"
else
  KANON="kanon"
fi

# --- Prerequisites ---
if ! command -v kiro-cli &>/dev/null; then
  echo "SKIP: kiro-cli not found on PATH"
  exit 2
fi
if ! command -v kanon &>/dev/null && [[ ! -x "$KANON" ]]; then
  echo "SKIP: kanon not found on PATH or in .venv"
  exit 2
fi

# --- Helpers ---
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

log() { echo "[$(date +%H:%M:%S)] $*"; }

run_depth_test() {
  local depth=$1
  local workdir
  workdir=$(mktemp -d)
  trap "rm -rf '$workdir'" RETURN

  log "=== DEPTH $depth ==="
  log "Scaffolding project at $workdir..."

  # Scaffold
  if [[ $depth -eq 0 ]]; then
    "$KANON" init "$workdir" --aspects "kanon-sdd:0" --quiet
  else
    "$KANON" init "$workdir" --aspects "kanon-sdd:$depth" --quiet
  fi

  # Init git (for file ordering tracking)
  git -C "$workdir" init -q
  git -C "$workdir" add -A
  git -C "$workdir" commit -q -m "scaffold"

  # Create src/ so the agent has somewhere to write
  mkdir -p "$workdir/src"
  touch "$workdir/src/__init__.py"
  git -C "$workdir" add -A
  git -C "$workdir" commit -q -m "add src"

  log "Spawning kiro-cli (timeout: ${TIMEOUT}s)..."

  # Run kiro from the project directory
  local transcript="$workdir/.kiro-transcript.log"
  cd "$workdir"
  timeout "$TIMEOUT" kiro-cli chat \
    --no-interactive \
    --trust-all-tools \
    "$PROMPT" \
    2>&1 | tee "$transcript" || true
  cd - >/dev/null

  # --- Assertions per depth ---
  local pass=true

  case $depth in
    0)
      # Depth 0: Agent should just write code. No plan/spec/design required.
      if find "$workdir/src" -name "*.py" -newer "$workdir/src/__init__.py" | grep -q .; then
        log "  ✓ Source files created (agent wrote code)"
      else
        log "  ✗ No source files created"
        pass=false
      fi
      # Should NOT have created ceremony docs (not required at depth 0)
      if [[ -d "$workdir/docs/plans" ]] && find "$workdir/docs/plans" -name "*.md" | grep -q .; then
        log "  ⚠ Plan created at depth 0 (unnecessary but not wrong)"
      fi
      ;;

    1)
      # Depth 1: Agent must create a plan before source code.
      # Check for NEW plan files (not scaffolded ones — those are empty dirs)
      local new_plans
      new_plans=$(git -C "$workdir" diff --name-only HEAD -- 'docs/plans/*.md' 2>/dev/null || true)
      local new_src
      new_src=$(find "$workdir/src" -name "*.py" -newer "$workdir/src/__init__.py" 2>/dev/null | grep -v __init__ || true)

      if [[ -n "$new_plans" ]]; then
        log "  ✓ Plan file created: $new_plans"
      else
        # Also check untracked files
        new_plans=$(find "$workdir/docs/plans" -name "*.md" -newer "$workdir/.git/index" 2>/dev/null || true)
        if [[ -n "$new_plans" ]]; then
          log "  ✓ Plan file created (untracked): $new_plans"
        else
          log "  ✗ FAIL: No new plan file created in docs/plans/"
          pass=false
        fi
      fi

      if [[ -n "$new_src" ]] && [[ -z "$new_plans" ]]; then
        log "  ✗ FAIL: Source code written WITHOUT a plan (gate violation!)"
        pass=false
      fi

      # Check audit sentence in transcript
      if grep -qi "plan at" "$transcript" 2>/dev/null; then
        log "  ✓ Audit sentence found in transcript"
      else
        log "  ⚠ Audit sentence not found (may be acceptable if plan was written)"
      fi
      ;;

    2)
      # Depth 2: Agent must create a spec before planning.
      if find "$workdir/docs/specs" -name "*.md" 2>/dev/null | grep -q .; then
        log "  ✓ Spec file created (docs/specs/*.md)"
      else
        log "  ✗ FAIL: No spec file found in docs/specs/"
        pass=false
      fi
      if find "$workdir/docs/plans" -name "*.md" 2>/dev/null | grep -q .; then
        log "  ✓ Plan file also created"
      else
        log "  ⚠ No plan file (may have been combined with spec)"
      fi
      ;;

    3)
      # Depth 3: Agent must create a design doc.
      if find "$workdir/docs/design" -name "*.md" 2>/dev/null | grep -q .; then
        log "  ✓ Design doc created (docs/design/*.md)"
      else
        log "  ✗ FAIL: No design doc found in docs/design/"
        pass=false
      fi
      if find "$workdir/docs/specs" -name "*.md" 2>/dev/null | grep -q .; then
        log "  ✓ Spec file also created"
      else
        log "  ⚠ No spec file (may have been combined with design)"
      fi
      ;;
  esac

  # --- Verdict ---
  if [[ "$pass" == "true" ]]; then
    log "  ✅ DEPTH $depth: PASS"
    ((PASS_COUNT++))
  else
    log "  ❌ DEPTH $depth: FAIL"
    log "  Transcript saved: $transcript"
    ((FAIL_COUNT++))
  fi
}

# --- Main ---
DEPTH="${1:-1}"

if [[ "$DEPTH" == "all" ]]; then
  for d in 0 1 2 3; do
    run_depth_test "$d"
  done
else
  run_depth_test "$DEPTH"
fi

# --- Summary ---
echo ""
echo "=== SUMMARY ==="
echo "  PASS: $PASS_COUNT"
echo "  FAIL: $FAIL_COUNT"
echo ""

if [[ $FAIL_COUNT -gt 0 ]]; then
  echo "RESULT: FAIL"
  exit 1
else
  echo "RESULT: PASS"
  exit 0
fi
