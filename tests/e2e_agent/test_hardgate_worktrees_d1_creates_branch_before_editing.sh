#!/usr/bin/env bash
# test_hardgate_worktrees_d1_creates_branch_before_editing.sh — Worktree gate: mentions worktree.
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
require_kiro

init_project 1 ",kanon-worktrees:1"

run_agent "Add a hello_world function to src/utils.py that returns 'Hello, World!'."

assert_pass "Transcript mentions worktree" transcript_contains "worktree\|wt/\|\.worktrees" || fail

verdict "WORKTREES_D1_BRANCH_BEFORE_EDITING"
