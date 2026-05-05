#!/usr/bin/env bash
# test_hardgate_sdd_d2_specs_before_planning.sh — D2: new capability → spec first.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 2

run_agent "Add a new user authentication system to this project. It should support email/password login and JWT tokens. This is a new user-visible capability. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

assert_pass "Spec created" has_new_docs specs || fail
assert_pass "Mentions vision/foundations" transcript_contains "vision\|foundation" || fail

verdict "D2_SPECS_BEFORE_PLANNING"
