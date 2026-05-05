"""Gate discovery and evaluation engine."""
from __future__ import annotations

import datetime
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from kanon_core._manifest import _aspect_path, _aspect_protocols, _parse_frontmatter


def discover_gates(aspects: dict[str, int]) -> list[dict[str, Any]]:
    """Discover active hard gates from protocol frontmatter, filtered by depth."""
    gates: list[dict[str, Any]] = []
    for aspect, depth in aspects.items():
        aspect_root = _aspect_path(aspect)
        for proto_file in _aspect_protocols(aspect, depth):
            proto_path = aspect_root / "protocols" / proto_file
            if not proto_path.exists():
                continue
            fm = _parse_frontmatter(proto_path.read_text(encoding="utf-8"))
            if fm.get("gate") != "hard":
                continue
            if depth < fm.get("depth-min", 1):
                continue
            gates.append({
                "label": fm.get("label", proto_file),
                "aspect": aspect,
                "protocol": proto_file,
                "priority": fm.get("priority", 500),
                "check": fm.get("check"),
                "question": fm.get("question", ""),
                "audit": fm.get("audit", ""),
                "skip_when": fm.get("skip-when", ""),
            })
    gates.sort(key=lambda g: g["priority"])
    return gates


def evaluate_gates(
    gates: list[dict[str, Any]], target: Path, *, fail_fast: bool = False
) -> list[dict[str, Any]]:
    """Run check commands for gates that have them. Returns results list."""
    results: list[dict[str, Any]] = []
    for gate in gates:
        result: dict[str, Any] = {
            "label": gate["label"],
            "aspect": gate["aspect"],
            "protocol": gate["protocol"],
            "priority": gate["priority"],
            "check": gate["check"],
        }
        if gate["check"] is None:
            result["status"] = "judgment"
            result["question"] = gate["question"]
            result["audit"] = gate["audit"]
            result["skip_when"] = gate["skip_when"]
            result["exit_code"] = None
            result["duration_s"] = 0.0
        else:
            start = time.monotonic()
            try:
                proc = subprocess.run(
                    gate["check"],
                    shell=True,  # noqa: S602 — ADR-0036 trust model
                    cwd=str(target),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                result["status"] = "pass" if proc.returncode == 0 else "fail"
                result["exit_code"] = proc.returncode
            except subprocess.TimeoutExpired:
                result["status"] = "fail"
                result["exit_code"] = -1
            result["duration_s"] = round(time.monotonic() - start, 3)
        results.append(result)
        if fail_fast and result["status"] == "fail":
            break
    return results


def write_trace(target: Path, results: list[dict[str, Any]]) -> None:
    """Append invocation trace to .kanon/traces/gates.jsonl."""
    traces_dir = target / ".kanon" / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    trace_file = traces_dir / "gates.jsonl"
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cwd": str(Path.cwd()),
        "gates": [{"label": r["label"], "status": r["status"]} for r in results],
        "passed": all(r["status"] != "fail" for r in results),
    }
    with trace_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
