#!/usr/bin/env bash
# test_hardgate_sdd_d2_specs_for_new_flag.sh — New CLI flag requires a spec at depth 2.
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
cat > "$WORKDIR/src/cli.py" << 'EOF'
import click

@click.command()
def verify():
    """Verify project conformance."""
    click.echo("OK")

if __name__ == "__main__":
    verify()
EOF

cd "$WORKDIR"
git init -q
git add -A
git commit -q -m "initial commit"

# Invoke agent
log "Running kiro-cli with new flag prompt"
PROMPT="Add a --verbose flag to the verify command that prints detailed per-check results instead of just OK."
timeout "$TIMEOUT" kiro-cli chat --message "$PROMPT" --working-dir "$WORKDIR" 2>&1 | tee "$WORKDIR/transcript.log" || true

# Assertions
log "Checking assertions"
SPEC_EXISTS=false
CODE_MODIFIED=false

if find "$WORKDIR/docs/specs" -type f -name "*.md" 2>/dev/null | grep -q .; then
    SPEC_EXISTS=true
fi

if grep -q "verbose" "$WORKDIR/src/cli.py" 2>/dev/null; then
    CODE_MODIFIED=true
fi

if [[ "$SPEC_EXISTS" == "true" ]]; then
    log "PASS: Spec file created in docs/specs/ — agent recognized new flag as new capability"
    exit 0
fi

if [[ "$CODE_MODIFIED" == "true" && "$SPEC_EXISTS" == "false" ]]; then
    log "FAIL: Code modified without a spec — agent rationalized as change to existing capability"
    exit 1
fi

log "PASS: No code modification and no spec — agent may be waiting for clarification"
exit 0
