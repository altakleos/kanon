#!/usr/bin/env bash
# test_hardgate_sdd_d2_plans_but_skips_spec_for_bugfix.sh — D2: bugfix needs plan not spec.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 2

cat > src/pool.py << 'EOF'
class ConnectionPool:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.connections = []
EOF

cat > src/retry.py << 'EOF'
from src.pool import ConnectionPool

def retry_with_pool(pool: ConnectionPool, func, retries: int = 3):
    """Retry func using pool's connection settings."""
    pool.timeout = 5  # BUG: overwrites pool's configured timeout
    for attempt in range(retries):
        try:
            return func()
        except Exception:
            if attempt == retries - 1:
                raise
EOF
git add -A && git commit -q -m "add pool and retry"

run_agent "Fix the bug in src/retry.py where it overwrites the pool timeout with a hardcoded value of 5. The retry function should respect the pool's configured timeout."

assert_fail "No spec for bugfix" has_new_docs specs || fail
assert_pass "Hardcoded timeout removed" bash -c '! grep -q "pool.timeout = 5" src/retry.py' || fail

verdict "D2_BUGFIX_PLAN_NOT_SPEC"
