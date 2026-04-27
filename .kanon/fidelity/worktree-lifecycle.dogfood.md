# Dogfood capture: worktree-lifecycle

Captured 2026-04-27 against an AGENT session asked to fix a typo in a
source file. The session begins on a clean main checkout; the AGENT
creates a worktree before any edits, performs the change, and tears
down via the helper script (never `--force`).

USER: Please fix the typo `recieve` → `receive` in src/widget.py near line 84. It's been bugging me.

AGENT: Working in worktree `.worktrees/typo-fix/` on branch `wt/typo-fix`. Setting up the isolation now and I'll do the edit there.

USER: Sounds good. Let me know when it's done.

AGENT: Edit applied at src/widget.py:84. ruff and mypy are clean; the targeted pytest case passes. Committed as `fix: spelling — recieve → receive in widget` on `wt/typo-fix`.

USER: Open the PR.

AGENT: Pushed `wt/typo-fix` to origin and opened PR-ZZ. After the merge I'll tear down the worktree with `bash scripts/worktree-teardown.sh typo-fix` (never `--force`; the script refuses on uncommitted state).

USER: Thanks.

AGENT: Done. Branch deleted locally; worktree removed cleanly.
