#!/usr/bin/env bash
# test_hardgate_sdd_d1_plans_before_coding.sh — D1: plans before coding.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 1

run_agent "Add a function called 'paginate' to src/utils.py that takes a list, page number, and page size, and returns the appropriate slice. Include type hints and a docstring. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

assert_pass "Plan created" has_new_docs plans || fail

# Hard gate: if code exists without a plan, that's a failure
if has_new_source && ! has_new_docs plans; then
  log "  ✗ FAIL: Code without plan"
  fail
fi

verdict "D1_PLANS_BEFORE_CODING"
