#!/usr/bin/env bash
# test_hardgate_sdd_d1_builds_from_existing_plan.sh — D1: existing plan → implements.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 1

mkdir -p docs/plans
cat > docs/plans/add-cache.md << 'EOF'
# Plan: Add TTL Cache Module

**Status:** done

## Steps
1. Create src/cache.py with a TTLCache class
2. TTLCache stores key-value pairs with a configurable TTL
3. Expired entries are lazily evicted on access

## Acceptance Criteria
- [ ] `TTLCache(ttl=60)` creates a cache with 60s TTL
- [ ] `.set(key, value)` stores an entry
- [ ] `.get(key)` returns value or None if expired
EOF
git add -A && git commit -q -m "add plan"

PLAN_COUNT=$(find docs/plans -type f -name "*.md" ! -name "_template.md" ! -name "README.md" | wc -l)

run_agent "Implement the cache module per the approved plan at docs/plans/add-cache.md."

assert_pass "TTLCache implemented" grep -q "class TTLCache" src/cache.py || fail

NEW_PLAN_COUNT=$(find docs/plans -type f -name "*.md" ! -name "_template.md" ! -name "README.md" | wc -l)
if [[ "$NEW_PLAN_COUNT" -gt "$PLAN_COUNT" ]]; then
  log "  ✗ FAIL: New plan created (should reuse existing)"
  fail
else
  log "  ✓ No new plan created"
fi

verdict "D1_BUILDS_FROM_EXISTING_PLAN"
