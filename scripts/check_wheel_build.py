"""Pre-tag wheel-build validator (maintainer-side).

Builds a fresh sdist + wheel via the same `python -m build` invocation
that `.github/workflows/release.yml` runs on tag push, then validates
the produced wheel via `scripts/check_package_contents.py`. Closes the
gap that produced v0.5.0a2 hotfixes #99 + #100 — local validation that
ran `python -m build --wheel` (direct, no sdist) bypassed the
sdist-include filter and produced a complete wheel even when the actual
sdist→wheel CI pipeline was broken.

Usage:
    python scripts/check_wheel_build.py --tag v0.5.0a2
    python scripts/check_wheel_build.py            # uses kernel.__version__

Invokes `uv tool run --from build python -m build` so `build` need not
be in the project's runtime/dev dependencies. Wipes `dist/` first.

Exit codes:
    0  — sdist+wheel built and validation passed
    1  — build failed
    2  — validation reported missing files / forbidden paths / etc.
    3  — wheel not found in dist/ after build

Prints a single JSON object to stdout regardless of exit code.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DIST = _REPO_ROOT / "dist"
_VALIDATOR = _REPO_ROOT / "scripts" / "check_package_contents.py"
_KERNEL_INIT = _REPO_ROOT / "kernel" / "__init__.py"
_VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _read_kernel_version() -> str | None:
    if not _KERNEL_INIT.is_file():
        return None
    m = _VERSION_PATTERN.search(_KERNEL_INIT.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _build(cwd: Path) -> tuple[int, str]:
    if _DIST.is_dir():
        shutil.rmtree(_DIST)
    cmd = ["uv", "tool", "run", "--from", "build", "python", "-m", "build"]
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)


def _find_wheel() -> Path | None:
    if not _DIST.is_dir():
        return None
    wheels = sorted(_DIST.glob("*.whl"))
    return wheels[0] if wheels else None


def _validate(wheel: Path, tag: str, cwd: Path) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, str(_VALIDATOR), "--wheel", str(wheel), "--tag", tag]
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {"status": "validator-output-unparseable", "stdout": proc.stdout, "stderr": proc.stderr}
    return proc.returncode, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--tag",
        default=None,
        help="Release tag, e.g. v0.5.0a2. Defaults to 'v' + kernel.__version__.",
    )
    args = parser.parse_args(argv)

    tag = args.tag
    if tag is None:
        version = _read_kernel_version()
        if version is None:
            print(json.dumps({"ok": False, "phase": "tag-resolution", "error": "could not read kernel.__version__"}))
            return 1
        tag = f"v{version}"

    rc, build_log = _build(_REPO_ROOT)
    if rc != 0:
        print(json.dumps({"ok": False, "phase": "build", "tag": tag, "build_exit": rc, "log_tail": build_log[-1000:]}))
        return 1

    wheel = _find_wheel()
    if wheel is None:
        print(json.dumps({"ok": False, "phase": "wheel-discovery", "tag": tag, "dist_dir": str(_DIST)}))
        return 3

    val_rc, val_report = _validate(wheel, tag, _REPO_ROOT)
    out: dict[str, Any] = {
        "ok": val_rc == 0,
        "tag": tag,
        "wheel": str(wheel.relative_to(_REPO_ROOT)),
        "validation": val_report,
    }
    print(json.dumps(out))
    return 0 if val_rc == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
