#!/usr/bin/env bash
# test_protocol_sdd_d2_respects_existing_vision.sh — D2: populated vision → no foundations offer.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 2

mkdir -p docs/foundations
cat > docs/foundations/vision.md << 'EOF'
# Vision

## Mission
Build a fast, reliable CLI tool for project scaffolding.

## Non-goals
- GUI interface
- Cloud deployment
- Plugin marketplace

## Key Bets
- Convention over configuration reduces onboarding time
- Opinionated defaults beat infinite flexibility
- Local-first execution keeps the tool fast
EOF
git add -A && git commit -q -m "populate vision"

run_agent "Add a new 'export' command that exports the project configuration as YAML to stdout. This is a new user-visible capability. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

assert_pass "Spec created" has_new_docs specs || fail
assert_pass "No foundations prompt" transcript_lacks "foundations are empty\|populate foundations\|write a vision" || fail

verdict "D2_RESPECTS_EXISTING_VISION"
