#!/usr/bin/env bash
# test_hardgate_sdd_d0_codes_without_ceremony.sh — D0: codes freely without ceremony.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 0

run_agent "Add a function called 'paginate' to src/utils.py that takes a list, page number, and page size, and returns the appropriate slice. Include type hints and a docstring."

assert_pass "Agent wrote source code" has_new_source || fail

verdict "D0_CODES_FREELY"
