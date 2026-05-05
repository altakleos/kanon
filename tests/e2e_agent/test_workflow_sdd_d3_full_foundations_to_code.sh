#!/usr/bin/env bash
# test_workflow_sdd_d3_full_foundations_to_code.sh — Complete depth-3 lifecycle from empty project:
# vision → principles/personas → spec → design → plan → code
set -euo pipefail
TIMEOUT=600  # 10 minutes — full lifecycle is longer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then KANON="$REPO_ROOT/.venv/bin/kanon"; else KANON="kanon"; fi
if ! command -v kiro-cli &>/dev/null; then echo "SKIP: kiro-cli not found"; exit 2; fi
log() { echo "[$(date +%H:%M:%S)] $*"; }

WORKDIR=$(mktemp -d)
trap "rm -rf '$WORKDIR'" EXIT

log "=== WORKFLOW: FULL FOUNDATIONS → CODE LIFECYCLE ==="
log "Scaffolding depth-3 project with empty foundations..."
"$KANON" init "$WORKDIR" --aspects "kanon-sdd:3" --quiet
mkdir -p "$WORKDIR/src" && touch "$WORKDIR/src/__init__.py"
cd "$WORKDIR" && git init -q && git add -A && git commit -q -m "init"

PROMPT="Build a task queue system for this project. It should support async workers, priority scheduling, and dead-letter handling. This is a brand new project — start from the foundations: define the vision, identify key principles and personas, then write the spec, design, plan, and implement. This introduces new component boundaries (scheduler, worker pool, dead-letter store)."

log "Spawning kiro-cli (timeout: ${TIMEOUT}s)..."
TRANSCRIPT="$WORKDIR/.transcript.log"
timeout "$TIMEOUT" kiro-cli chat --no-interactive --trust-all-tools "$PROMPT" 2>&1 | tee "$TRANSCRIPT" || true

# --- Assertions ---
PASS=true

# 1. Vision populated (not just template)
VISION="docs/foundations/vision.md"
if [[ -f "$VISION" ]]; then
  # Check it's not just the scaffold template (template has "TODO" or is < 100 bytes of real content)
  VISION_SIZE=$(wc -c < "$VISION" | tr -d ' ')
  if [[ "$VISION_SIZE" -gt 200 ]] && ! grep -qi "TODO.*fill" "$VISION"; then
    log "  ✓ Vision populated ($VISION_SIZE bytes)"
  else
    log "  ⚠ Vision exists but may still be template"
  fi
else
  log "  ⚠ No vision file (agent may have skipped foundations)"
fi

# 2. Principles or personas populated
PRINCIPLES=$(find docs/foundations/principles -name "*.md" -newer .git/index 2>/dev/null | grep -v _template || true)
PERSONAS=$(find docs/foundations/personas -name "*.md" -newer .git/index 2>/dev/null | grep -v _template || true)
if [[ -n "$PRINCIPLES" ]] || [[ -n "$PERSONAS" ]]; then
  log "  ✓ Foundations artifacts created: ${PRINCIPLES}${PERSONAS}"
else
  log "  ⚠ No principles/personas created (soft protocol — not a hard failure)"
fi

# 3. Spec must exist
SPECS=$(find docs/specs -name "*.md" -newer .git/index 2>/dev/null || true)
if [[ -n "$SPECS" ]]; then
  log "  ✓ Spec created: $SPECS"
else
  log "  ✗ FAIL: No spec created"
  PASS=false
fi

# 4. Design doc must exist
DESIGNS=$(find docs/design -name "*.md" -newer .git/index 2>/dev/null || true)
if [[ -n "$DESIGNS" ]]; then
  log "  ✓ Design doc created: $DESIGNS"
else
  log "  ✗ FAIL: No design doc created"
  PASS=false
fi

# 5. Plan must exist
PLANS=$(find docs/plans -name "*.md" -newer .git/index 2>/dev/null || true)
if [[ -n "$PLANS" ]]; then
  log "  ✓ Plan created: $PLANS"
else
  log "  ⚠ No plan yet (agent may have stopped for approval — acceptable)"
fi

# 6. Ordering check: spec before design before plan
if [[ -n "$SPECS" ]] && [[ -n "$DESIGNS" ]]; then
  SPEC_FILE=$(echo "$SPECS" | head -1)
  DESIGN_FILE=$(echo "$DESIGNS" | head -1)
  SPEC_TIME=$(stat -f %m "$SPEC_FILE" 2>/dev/null || stat -c %Y "$SPEC_FILE")
  DESIGN_TIME=$(stat -f %m "$DESIGN_FILE" 2>/dev/null || stat -c %Y "$DESIGN_FILE")
  if [[ "$SPEC_TIME" -le "$DESIGN_TIME" ]]; then
    log "  ✓ Correct order: spec before design"
  else
    log "  ✗ FAIL: Design created before spec"
    PASS=false
  fi
fi

# 7. No source code without spec + design
SRC=$(find src -name "*.py" -newer src/__init__.py 2>/dev/null | grep -v __init__ || true)
if [[ -n "$SRC" ]] && [[ -z "$SPECS" ]]; then
  log "  ✗ FAIL: Source code written without spec"
  PASS=false
fi
if [[ -n "$SRC" ]] && [[ -z "$DESIGNS" ]]; then
  log "  ✗ FAIL: Source code written without design doc"
  PASS=false
fi

# --- Verdict ---
log ""
log "  Artifacts found:"
log "    Vision:     $(test -f "$VISION" && echo "✓" || echo "✗")"
log "    Principles: $(test -n "$PRINCIPLES" && echo "✓" || echo "-")"
log "    Personas:   $(test -n "$PERSONAS" && echo "✓" || echo "-")"
log "    Spec:       $(test -n "$SPECS" && echo "✓" || echo "✗")"
log "    Design:     $(test -n "$DESIGNS" && echo "✓" || echo "✗")"
log "    Plan:       $(test -n "$PLANS" && echo "✓" || echo "-")"
log "    Code:       $(test -n "$SRC" && echo "✓" || echo "-")"
log ""

if [[ "$PASS" == "true" ]]; then
  log "  ✅ FULL LIFECYCLE: PASS"
  exit 0
else
  log "  ❌ FULL LIFECYCLE: FAIL"
  log "  Transcript: $TRANSCRIPT"
  exit 1
fi
