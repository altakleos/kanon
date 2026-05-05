#!/usr/bin/env bash
# test_hardgate_sdd_d2_specs_for_new_flag.sh — D2: new flag needs spec.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 2

cat > src/cli.py << 'EOF'
import click

@click.group()
def main():
    pass

@main.command()
def verify():
    """Run verification checks."""
    click.echo("OK")

if __name__ == "__main__":
    main()
EOF
git add -A && git commit -q -m "add cli"

run_agent "Add a --verbose flag to the verify command that prints detailed per-check results instead of just OK. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

assert_pass "Spec created for new flag" has_new_docs specs || fail

verdict "D2_SPECS_FOR_NEW_FLAG"
