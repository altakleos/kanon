"""Staged local validation — the ``kanon preflight`` engine."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from kanon._manifest import (
    _aspect_depth_range,
    _load_aspect_manifest,
    _render_placeholder,
)

_STAGES = ("commit", "push", "release")


def _resolve_preflight_checks(
    aspects: dict[str, int],
    config: dict[str, Any],
    stage: str,
) -> list[dict[str, str]]:
    """Build the ordered check list for *stage* by merging aspect defaults + consumer overrides."""
    # Collect aspect-contributed defaults.
    aspect_defaults: dict[str, list[dict[str, str]]] = {s: [] for s in _STAGES}
    for aspect, depth in sorted(aspects.items()):
        sub = _load_aspect_manifest(aspect)
        # Build config context for placeholder resolution.
        aspect_config = config.get("aspects", {}).get(aspect, {}).get("config", {})
        ctx = {k: str(v) for k, v in aspect_config.items()}
        min_d, _ = _aspect_depth_range(aspect)
        for d in range(min_d, depth + 1):
            depth_entry = sub.get(f"depth-{d}", {})
            for s, checks in depth_entry.get("preflight", {}).items():
                if s not in _STAGES:
                    continue
                for check in checks or []:
                    run_cmd = _render_placeholder(check.get("run", ""), ctx)
                    if not run_cmd.strip() or "${" in run_cmd:
                        continue  # empty or unresolved placeholder — skip
                    aspect_defaults[s].append({
                        "run": run_cmd,
                        "label": check.get("label", run_cmd),
                    })

    # Consumer overrides from preflight-stages: in config.
    consumer_stages: dict[str, list[dict[str, str]]] = {}
    for s, checks in config.get("preflight-stages", {}).items():
        if s in _STAGES and checks:
            consumer_stages[s] = [
                {"run": c["run"], "label": c.get("label", c["run"])}
                for c in checks
            ]

    # Merge: consumer overrides by label, appends new labels.
    resolved: dict[str, list[dict[str, str]]] = {}
    for s in _STAGES:
        defaults = aspect_defaults.get(s, [])
        overrides = consumer_stages.get(s)
        if overrides is None:
            resolved[s] = defaults
        else:
            override_labels = {c["label"] for c in overrides}
            merged = [c for c in defaults if c["label"] not in override_labels]
            merged.extend(overrides)
            resolved[s] = merged

    # Build run list: strict superset up to requested stage.
    run_list: list[dict[str, str]] = []
    for s in _STAGES:
        run_list.extend(resolved.get(s, []))
        if s == stage:
            break
    return run_list


def _run_preflight(
    target: Path,
    checks: list[dict[str, str]],
    tag: str | None,
    fail_fast: bool,
) -> tuple[bool, list[dict[str, Any]]]:
    """Execute checks sequentially. Returns (all_passed, results)."""
    env = os.environ.copy()
    if tag:
        env["TAG"] = tag
    results: list[dict[str, Any]] = []
    all_passed = True
    for check in checks:
        cmd = check["run"]
        label = check["label"]
        t0 = time.monotonic()
        try:
            # `shell=True` here is governed by ADR-0036 / secure-defaults
            # § Trust-boundary carve-out: `cmd` is sourced from
            # `.kanon/config.yaml` (or aspect manifest `preflight:` entries),
            # both inside the same repo as the running CLI. Trust boundary
            # is repo write-access. Refactoring to argv form would silently
            # break consumer commands using shell features (`$VAR`, `&&`,
            # pipes, redirection).
            proc = subprocess.run(  # nosec — see ADR-0036
                cmd, shell=True, cwd=str(target), env=env,
                capture_output=True, text=True,
            )
            passed = proc.returncode == 0
        except Exception:
            passed = False
        duration = round(time.monotonic() - t0, 1)
        mark = "✓" if passed else "✗"
        print(f"{mark} {label}: {cmd}  {duration}s", file=sys.stderr)
        results.append({
            "label": label,
            "command": cmd,
            "passed": passed,
            "duration_s": duration,
        })
        if not passed:
            all_passed = False
            if fail_fast:
                break
    return all_passed, results
