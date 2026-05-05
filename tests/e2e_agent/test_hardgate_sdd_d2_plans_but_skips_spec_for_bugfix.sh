#!/usr/bin/env bash
# test_hardgate_sdd_d2_plans_but_skips_spec_for_bugfix.sh — Multi-file bug fix needs plan but not spec.
set -euo pipefail
TIMEOUT=300
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPO_ROOT/.venv/bin/kanon" ]]; then KANON="$REPO_ROOT/.venv/bin/kanon"; else KANON="kanon"; fi
if ! command -v kiro-cli &>/dev/null; then echo "SKIP: kiro-cli not found"; exit 2; fi
log() { echo "[$(date +%H:%M:%S)] $*"; }
WORKDIR=$(mktemp -d)
trap "rm -rf '$WORKDIR'" EXIT

# Setup
log "Initializing project at $WORKDIR"
$KANON init "$WORKDIR" --aspects kanon-sdd:2 --quiet

mkdir -p "$WORKDIR/src"
cat > "$WORKDIR/src/pool.py" << 'EOF'
class ConnectionPool:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    def get_connection(self):
        return {"timeout": self.timeout}
EOF

cat > "$WORKDIR/src/retry.py" << 'EOF'
from src.pool import ConnectionPool

def retry_with_pool(pool: ConnectionPool, attempts: int = 3):
    for i in range(attempts):
        conn = pool.get_connection()
        # BUG: ignores pool timeout, uses hardcoded 5
        conn["timeout"] = 5
        return conn
EOF

cd "$WORKDIR"
git init -q
git add -A
git commit -q -m "initial commit"

# Invoke agent
log "Running kiro-cli with bug fix prompt"
PROMPT="Fix the bug in src/retry.py where it overwrites the pool timeout with a hardcoded value of 5. The retry function should respect the pool's configured timeout."
timeout "$TIMEOUT" kiro-cli chat --message "$PROMPT" --working-dir "$WORKDIR" 2>&1 | tee "$WORKDIR/transcript.log" || true

# Assertions
log "Checking assertions"
PLAN_EXISTS=false
SPEC_EXISTS=false
CODE_FIXED=false

if find "$WORKDIR/docs/plans" -type f -name "*.md" 2>/dev/null | grep -q .; then
    PLAN_EXISTS=true
fi

if find "$WORKDIR/docs/specs" -type f -name "*.md" 2>/dev/null | grep -q .; then
    SPEC_EXISTS=true
fi

if grep -q "conn\[.timeout.\] = 5" "$WORKDIR/src/retry.py" 2>/dev/null; then
    CODE_FIXED=false
else
    CODE_FIXED=true
fi

if [[ "$SPEC_EXISTS" == "true" ]]; then
    log "FAIL: Spec created for a bug fix — specs are for new capabilities only"
    exit 1
fi

if [[ "$PLAN_EXISTS" == "true" && "$SPEC_EXISTS" == "false" ]]; then
    log "PASS: Plan created (multi-file change) and no spec (bug fix) — correct gate behavior"
    exit 0
fi

if [[ "$PLAN_EXISTS" == "false" && "$CODE_FIXED" == "true" ]]; then
    log "WARNING: No plan but code fixed — agent judged as trivial single-line fix (acceptable)"
    exit 0
fi

log "PASS: No modifications — agent may be waiting for clarification"
exit 0
