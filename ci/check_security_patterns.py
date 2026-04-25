#!/usr/bin/env python3
"""Security pattern scanner. Language-agnostic regex-based detection of common anti-patterns.

Usage: python ci/check_security_patterns.py [--root DIR]

Best-effort safety net — not a SAST replacement. Findings are warnings (exit 0).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

# File extensions to scan.
_EXTENSIONS = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".sh"}

# Directories to skip.
_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}

# --- patterns ---

_SQL_INTERP = re.compile(
    r"""(?:f['"]|['"].*%s|['"].*\.format\()"""
    r""".*?\b(?:SELECT|INSERT|UPDATE|DELETE)\b"""
    r"""|(?:SELECT|INSERT|UPDATE|DELETE)\b.*?\$\{""",
    re.IGNORECASE,
)

_TLS_DISABLED = re.compile(
    r"""verify\s*=\s*False"""
    r"""|rejectUnauthorized\s*[:=]\s*(?:false|0)"""
    r"""|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['"]?0""",
)

_PERMISSIVE_MODE = re.compile(
    r"""0o777|0777|chmod\s+777""",
)

_WILDCARD_CORS = re.compile(
    r"""Access-Control-Allow-Origin\s*:\s*\*"""
    r"""|origin\s*[:=]\s*['\"]\*['\"]""",
    re.IGNORECASE,
)


def _shannon_entropy(s: str) -> float:
    """Compute Shannon entropy of a string."""
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((n / length) * math.log2(n / length) for n in freq.values())


_HIGH_ENTROPY_TOKEN = re.compile(r"""['"][A-Za-z0-9+/=_\-]{21,}['"]""")


def _scan_file(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return findings

    for i, line in enumerate(lines, 1):
        lineno = i

        if _SQL_INTERP.search(line):
            findings.append({"file": str(path), "line": lineno, "rule": "sql-interpolation",
                             "message": "Possible string-interpolated SQL"})

        if _TLS_DISABLED.search(line):
            findings.append({"file": str(path), "line": lineno, "rule": "tls-disabled",
                             "message": "TLS verification appears disabled"})

        if _PERMISSIVE_MODE.search(line):
            findings.append({"file": str(path), "line": lineno, "rule": "permissive-mode",
                             "message": "Overly permissive file mode (777)"})

        if _WILDCARD_CORS.search(line):
            findings.append({"file": str(path), "line": lineno, "rule": "wildcard-cors",
                             "message": "Wildcard CORS origin"})

        for m in _HIGH_ENTROPY_TOKEN.finditer(line):
            token = m.group()[1:-1]  # strip quotes
            if _shannon_entropy(token) > 4.5:
                findings.append({"file": str(path), "line": lineno, "rule": "high-entropy-secret",
                                 "message": "High-entropy string — possible hardcoded secret"})
                break  # one finding per line is enough

    return findings


def _collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in sorted(root.rglob("*")):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix in _EXTENSIONS:
            files.append(p)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Security pattern scanner")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on findings")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    all_findings: list[dict[str, Any]] = []
    for f in _collect_files(root):
        all_findings.extend(_scan_file(f))

    status = "warn" if all_findings else "ok"
    report = {"status": status, "findings": all_findings}
    print(json.dumps(report, indent=2))
    sys.exit(1 if args.strict and all_findings else 0)


if __name__ == "__main__":
    main()
