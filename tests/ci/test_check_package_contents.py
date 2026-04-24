"""Tests for ci/check_package_contents.py."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "ci" / "check_package_contents.py"
assert _SCRIPT_PATH.is_file(), f"script not found: {_SCRIPT_PATH}"


def _load():
    spec = importlib.util.spec_from_file_location("check_package_contents", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


mod = _load()

_TAG = "v1.0.0"
_VERSION = "1.0.0"


def _build_wheel(tmp_path: Path, *, extra_files: dict[str, str] | None = None,
                 omit: set[str] | None = None, version: str = _VERSION) -> Path:
    """Create a minimal synthetic .whl with all required entries."""
    whl = tmp_path / "fake.whl"
    omit = omit or set()
    files: dict[str, str] = {}
    # Required files
    for f in mod.REQUIRED_FILES:
        if f in omit:
            continue
        if f == "kanon/__init__.py":
            files[f] = f'__version__ = "{version}"\n'
        else:
            files[f] = ""
    # Ensure required dirs have at least one entry
    for d in mod.REQUIRED_DIRS:
        if not any(k.startswith(d) for k in files):
            files[d + "_placeholder.txt"] = ""
    if extra_files:
        files.update(extra_files)
    # Also need a changelog for version concordance
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        f"# Changelog\n\n## [{version}] \u2014 2025-01-01\n\n- Initial\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(whl, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return whl


def test_valid_wheel_passes(tmp_path: Path) -> None:
    whl = _build_wheel(tmp_path)
    changelog = tmp_path / "CHANGELOG.md"
    rc, report = mod.check_wheel(whl, _TAG, changelog_path=changelog)
    assert rc == 0, f"expected exit 0, got {rc}: {report}"


def test_missing_required_file(tmp_path: Path) -> None:
    whl = _build_wheel(tmp_path, omit={"kanon/__init__.py"})
    changelog = tmp_path / "CHANGELOG.md"
    rc, report = mod.check_wheel(whl, _TAG, changelog_path=changelog)
    assert rc == 1


def test_forbidden_path_detected(tmp_path: Path) -> None:
    whl = _build_wheel(tmp_path, extra_files={"docs/something.md": ""})
    changelog = tmp_path / "CHANGELOG.md"
    rc, report = mod.check_wheel(whl, _TAG, changelog_path=changelog)
    assert rc == 2


def test_version_mismatch(tmp_path: Path) -> None:
    whl = _build_wheel(tmp_path, version="9.9.9")
    # Changelog matches the wheel version (9.9.9), but tag says v1.0.0
    changelog = tmp_path / "CHANGELOG.md"
    # Rewrite changelog to match tag so we isolate the version mismatch exit code
    changelog.write_text(
        "# Changelog\n\n## [1.0.0] \u2014 2025-01-01\n\n- Initial\n",
        encoding="utf-8",
    )
    rc, report = mod.check_wheel(whl, _TAG, changelog_path=changelog)
    assert rc == 3
