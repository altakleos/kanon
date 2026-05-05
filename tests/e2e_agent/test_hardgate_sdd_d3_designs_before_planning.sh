#!/usr/bin/env bash
# test_hardgate_sdd_d3_designs_before_planning.sh — D3: new boundaries → design doc.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 3

mkdir -p docs/specs
cat > docs/specs/plugin-system.md << 'EOF'
# Spec: Plugin System

**Status:** accepted

## Overview
A plugin system that allows extending the application via dynamically loaded modules.

## Requirements
- Plugin loader discovers .py files in a plugins/ directory
- Each plugin implements PluginInterface (ABC)
- Event dispatcher routes typed events to registered plugin handlers
- Plugins are isolated: one plugin's failure doesn't crash others

## Acceptance Criteria
- [ ] PluginInterface ABC with `on_event(event)` method
- [ ] PluginLoader discovers and loads plugins
- [ ] EventDispatcher routes events to handlers
EOF
git add -A && git commit -q -m "add spec"

run_agent "Implement the plugin system per the spec at docs/specs/plugin-system.md. This introduces new component boundaries: a plugin loader, a PluginInterface ABC, and an event dispatcher. All plans, specs, and designs are pre-approved — proceed through the full lifecycle without stopping for approval."

assert_pass "Design doc created" has_new_docs design || fail

verdict "D3_DESIGNS_BEFORE_PLANNING"
