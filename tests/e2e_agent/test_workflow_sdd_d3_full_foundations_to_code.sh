#!/usr/bin/env bash
# test_workflow_sdd_d3_full_foundations_to_code.sh — D3: full lifecycle from foundations.
TIMEOUT=600
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 3

run_agent "Build a task queue system for this project. It should support async workers, priority scheduling, and dead-letter handling. This is a brand new project — start from the foundations: define the vision, identify key principles and personas, then write the spec, design, plan, and implement. This introduces new component boundaries (scheduler, worker pool, dead-letter store). All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

# Hard gates
assert_pass "Spec created" has_new_docs specs || fail
assert_pass "Design created" has_new_docs design || fail

# Vision populated check
if [[ -f docs/foundations/vision.md ]]; then
  VISION_SIZE=$(wc -c < docs/foundations/vision.md)
  if [[ "$VISION_SIZE" -gt 200 ]] && ! grep -q "TODO" docs/foundations/vision.md; then
    log "  ✓ Vision populated (${VISION_SIZE} bytes, no TODOs)"
  else
    log "  ✗ FAIL: Vision too small or has TODOs"
    fail
  fi
else
  log "  ✗ FAIL: No vision file"
  fail
fi

# Ordering: spec and design both present
if has_new_docs specs && has_new_docs design; then
  log "  ✓ Both spec and design present (ordering assumed correct)"
fi

verdict "D3_FULL_FOUNDATIONS_TO_CODE"
