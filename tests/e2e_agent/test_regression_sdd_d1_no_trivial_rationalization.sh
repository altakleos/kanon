#!/usr/bin/env bash
# test_regression_sdd_d1_no_trivial_rationalization.sh — Regression: ambiguous prompt must not rationalize skip.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 1

cat > src/utils.py << 'EOF'
def get_first_page(items: list) -> list:
    """Get first 10 items."""
    return items[0:10]

def get_second_page(items: list) -> list:
    """Get second 10 items."""
    return items[10:20]
EOF
git add -A && git commit -q -m "add utils"

run_agent "Refactor src/utils.py to extract the repeated slice logic into a reusable helper called 'paginate'. Just cleaning up duplication."

# If code was written without a plan, that's rationalization
if grep -q "def paginate" src/utils.py && ! has_new_docs plans; then
  log "  ✗ FAIL: Code without plan (trivial rationalization)"
  fail
else
  log "  ✓ No rationalization detected"
fi

verdict "D1_NO_TRIVIAL_RATIONALIZATION"
