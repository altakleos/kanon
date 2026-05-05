#!/usr/bin/env bash
# test_hardgate_sdd_d1_skips_plan_for_typo.sh — D1: typo fix skips plan.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 1

cat > src/utils.py << 'EOF'
def greet(name: str) -> str:
    """Retrun a greeting message."""
    return f"Hello, {name}!"
EOF
git add -A && git commit -q -m "add utils"

run_agent "Fix the typo in the docstring of src/utils.py — 'Retrun' should be 'Return'."

assert_pass "Typo fixed" grep -q "Return a greeting" src/utils.py || fail
assert_fail "No plan for typo" has_new_docs plans || fail

verdict "D1_SKIPS_PLAN_FOR_TYPO"
