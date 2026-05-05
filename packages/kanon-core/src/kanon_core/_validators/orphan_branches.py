"""Validator: warn on wt/* branches with no corresponding worktree."""
from __future__ import annotations

import subprocess
from pathlib import Path


def check(target: str, errors: list[str], warnings: list[str]) -> None:
    """Check for orphaned wt/* branches."""
    worktrees_dir = Path(target) / ".worktrees"
    active_slugs = set()
    if worktrees_dir.is_dir():
        active_slugs = {d.name for d in worktrees_dir.iterdir() if d.is_dir()}

    try:
        result = subprocess.run(
            ["git", "branch", "--list", "wt/*"],
            cwd=str(target),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return
        for line in result.stdout.splitlines():
            branch = line.strip().lstrip("* ")
            if not branch.startswith("wt/"):
                continue
            slug = branch[3:]  # strip 'wt/' prefix
            if slug not in active_slugs:
                warnings.append(
                    f"Orphan branch: {branch} has no .worktrees/{slug}/ directory "
                    f"(merge or delete)"
                )
    except subprocess.TimeoutExpired:
        pass
