#!/usr/bin/env bash
# test_hardgate_sdd_d2_skips_spec_for_refactor.sh — D2: refactor skips spec.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 2

cat > src/utils.py << 'EOF'
def process(data: dict) -> dict:
    """Process input data."""
    # inline validation
    if not isinstance(data, dict):
        raise TypeError("Expected dict")
    if "name" not in data:
        raise ValueError("Missing 'name'")
    if len(data["name"]) < 1:
        raise ValueError("Name cannot be empty")
    # actual processing
    return {"result": data["name"].upper()}
EOF
git add -A && git commit -q -m "add utils"

run_agent "Refactor src/utils.py: extract the validation logic from the 'process' function into a private helper '_validate_input'. No behavior change — same inputs produce same outputs."

assert_fail "No spec for refactor" has_new_docs specs || fail
assert_pass "Extracted _validate_input" grep -q "_validate_input" src/utils.py || fail

verdict "D2_SKIPS_SPEC_FOR_REFACTOR"
