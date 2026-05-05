#!/usr/bin/env bash
# test_protocol_sdd_d2_foundations_extraction.sh — When vision is a template,
# agent populates it from user input and extracts principles/personas.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 2

run_agent "I want to populate the project foundations. Here's my vision: This project is a CLI tool that helps developers manage database migrations safely. It prioritizes zero-downtime deployments, reversibility of every migration, and clear error messages over speed. The primary users are backend developers who deploy to production weekly and DBAs who review migration safety. Please populate the vision, extract principles, and identify personas. All artifacts are pre-approved."

# Vision should be populated with real content
VISION="$WORKDIR/docs/foundations/vision.md"
if [[ -f "$VISION" ]] && [[ $(wc -c < "$VISION") -gt 200 ]]; then
  log "  ✓ Vision populated ($(wc -c < "$VISION" | tr -d ' ') bytes)"
else
  log "  ✗ FAIL: Vision not populated"
  fail
fi

# Principles should be extracted from vision
PRINCIPLES=$(find "$WORKDIR/docs/foundations/principles" -type f -name "*.md" ! -name "_template.md" ! -name "README.md" 2>/dev/null || true)
if [[ -n "$PRINCIPLES" ]]; then
  log "  ✓ Principles extracted: $(echo "$PRINCIPLES" | wc -l | tr -d ' ') file(s)"
else
  log "  ✗ FAIL: No principles extracted from vision"
  fail
fi

# Personas should be identified (at least one)
PERSONAS=$(find "$WORKDIR/docs/foundations/personas" -type f -name "*.md" ! -name "_template.md" ! -name "README.md" 2>/dev/null || true)
if [[ -n "$PERSONAS" ]]; then
  log "  ✓ Personas identified: $(echo "$PERSONAS" | wc -l | tr -d ' ') file(s)"
else
  log "  ⚠ No personas created (acceptable — may not be derivable)"
fi

verdict "D2_FOUNDATIONS_EXTRACTION"
