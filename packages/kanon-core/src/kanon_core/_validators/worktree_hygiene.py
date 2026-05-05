"""Validator: warn on stale worktrees (>7 days old or merged branches)."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path


def check(target: str, errors: list[str], warnings: list[str]) -> None:
    """Check for stale worktrees under .worktrees/."""
    worktrees_dir = Path(target) / ".worktrees"
    if not worktrees_dir.is_dir():
        return

    now = time.time()

    for wt in worktrees_dir.iterdir():
        if not wt.is_dir():
            continue
        # Check age via last commit
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct", "HEAD"],
                cwd=str(wt),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                last_commit = int(result.stdout.strip())
                age_days = (now - last_commit) / 86400
                if age_days > 7:
                    warnings.append(
                        f"Stale worktree: .worktrees/{wt.name}/ "
                        f"(last commit {int(age_days)} days ago)"
                    )
        except (subprocess.TimeoutExpired, ValueError):
            pass

        # Check if branch is merged to main
        branch_name = f"wt/{wt.name}"
        try:
            result = subprocess.run(
                ["git", "branch", "--merged", "main"],
                cwd=str(target),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and branch_name in result.stdout:
                warnings.append(
                    f"Merged worktree: .worktrees/{wt.name}/ "
                    f"(branch {branch_name} is merged to main — tear down)"
                )
        except subprocess.TimeoutExpired:
            pass
