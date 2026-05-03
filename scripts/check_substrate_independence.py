"""Substrate-independence gate (per ADR-0044).

Verifies that ``kanon-core``'s runtime code does not depend on
``kanon_reference`` being importable. The substrate's foundational invariant:
the kernel runs without the reference aspects.

Today's reality: the substrate and reference ship together as one ``kanon-kit``
wheel. The full ADR-0044 gate (separately-installed substrate wheel + clean
venv test run) is a future plan; this gate verifies the runtime contract by
spawning a sub-process with ``kanon_reference`` masked and exercising
substrate-internal queries that should not require it.

Failure mode: any substrate code that attempts ``import kanon_reference``
surfaces as ``ModuleNotFoundError`` in the sub-process and the gate fails.

Exit codes:
    0 — substrate runs without kanon_reference
    1 — substrate code attempted to import kanon_reference (or other failure)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

# The script that runs in the masked sub-process. Kept as a module-level
# constant so tests can introspect / monkeypatch it.
_SUBPROCESS_SCRIPT = '''
import sys
import os

# Mask kanon_reference imports via meta_path finder. Any code path that
# tries `import kanon_reference` or `from kanon_reference import X` raises.
class _BlockKanonReference:
    def find_spec(self, name, path=None, target=None):
        if name == "kanon_reference" or name.startswith("kanon_reference."):
            raise ImportError(
                f"substrate-independence gate (ADR-0044): {name!r} is masked; "
                f"substrate code MUST NOT depend on kanon_reference."
            )
        return None

sys.meta_path.insert(0, _BlockKanonReference())

# Also clear any existing cached kanon_reference imports from sys.modules
# so subsequent attempts go through the meta_path finder.
for mod in list(sys.modules):
    if mod == "kanon_reference" or mod.startswith("kanon_reference."):
        del sys.modules[mod]

# Substrate logic that must work without kanon_reference.
# Use KANON_TEST_OVERLAY_PATH to substitute the entry-point source so we
# don't trigger real entry-point loading (which may pull kanon_reference).
os.environ["KANON_TEST_OVERLAY_PATH"] = "/nonexistent/empty/overlay"

from kernel._manifest import _load_aspects_from_entry_points

aspects = _load_aspects_from_entry_points()
assert aspects == {}, f"expected empty registry, got {sorted(aspects)}"

# Verify _aspect_path falls through cleanly when no aspect is found.
from kernel._manifest import _aspect_path
import click
try:
    _aspect_path("nonexistent-aspect")
    raise AssertionError("expected ClickException")
except click.ClickException:
    pass

# Verify the resolutions engine works without kanon_reference.
from kernel._resolutions import replay, ReplayReport
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as td:
    report = replay(Path(td))
    assert isinstance(report, ReplayReport)
    assert report.ok, f"clean replay should succeed; got errors: {report.errors}"

# Verify the dialect grammar module imports + runs.
from kernel._dialects import validate_dialect_pin
validate_dialect_pin("2026-05-01")  # should not raise

# Verify the realization-shape module imports + runs.
from kernel._realization_shape import V1_DIALECT_VERBS, parse_realization_shape
assert "lint" in V1_DIALECT_VERBS

# Verify the composition module imports + runs.
from kernel._composition import compose
ordering, findings = compose([], surface="x")
assert ordering == [] and findings == []

print("substrate-independence: OK")
'''


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.parse_args(argv)

    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_SCRIPT],
        capture_output=True,
        text=True,
    )

    errors: list[str] = []
    warnings: list[str] = []
    if result.returncode != 0:
        errors.append(
            f"substrate-independence sub-process failed (exit {result.returncode})"
        )
        if result.stderr.strip():
            errors.append(f"stderr: {result.stderr.strip()}")
        if result.stdout.strip():
            errors.append(f"stdout: {result.stdout.strip()}")
    elif "substrate-independence: OK" not in result.stdout:
        errors.append(
            f"substrate-independence sub-process exited 0 but did not emit "
            f"the OK sentinel; stdout: {result.stdout.strip()!r}"
        )

    report: dict[str, Any] = {
        "errors": errors,
        "warnings": warnings,
        "status": "ok" if not errors else "fail",
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
