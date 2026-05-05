#!/usr/bin/env bash
# test_workflow_sdd_d2_full_spec_to_code.sh — D2: spec → plan → code workflow.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 2

run_agent "Add a rate limiter module to this project. It should provide a RateLimiter class that limits function calls to N per second using a token bucket algorithm. This is a new user-visible capability. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

# Hard gate
assert_pass "Spec created" has_new_docs specs || fail

# Soft checks (warn but don't fail)
if has_new_docs plans; then
  log "  ✓ Plan created"
else
  log "  ⚠ No plan (soft)"
fi

if has_new_source; then
  log "  ✓ Source created"
else
  log "  ⚠ No source (soft)"
fi

verdict "D2_FULL_SPEC_TO_CODE"
