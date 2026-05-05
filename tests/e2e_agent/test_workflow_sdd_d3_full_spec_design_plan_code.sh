#!/usr/bin/env bash
# test_workflow_sdd_d3_full_spec_design_plan_code.sh — D3: spec → design → plan → code.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 3

run_agent "Add an event bus system to this project. It should support publish/subscribe with typed events, async handlers, and a middleware pipeline. This is a new user-visible capability that introduces new component boundaries (event bus core, handler registry, middleware chain). All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

# Hard gates
assert_pass "Spec created" has_new_docs specs || fail
assert_pass "Design created" has_new_docs design || fail

# Soft checks
if has_new_docs plans; then
  log "  ✓ Plan created"
else
  log "  ⚠ No plan (soft)"
fi

# Ordering check: spec should be committed before design (by filename timestamp or git log)
if has_new_docs specs && has_new_docs design; then
  log "  ✓ Both spec and design present (ordering assumed correct)"
fi

verdict "D3_FULL_SPEC_DESIGN_PLAN_CODE"
