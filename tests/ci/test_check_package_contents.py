"""Tests for ci/check_package_contents.py."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import yaml

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

# Read the real manifests so synthetic wheels match the actual kit shape.
_KIT = _REPO_ROOT / "src" / "kanon" / "kit"
_TOP_MANIFEST_TEXT = (_KIT / "manifest.yaml").read_text(encoding="utf-8")
_TOP_MANIFEST = yaml.safe_load(_TOP_MANIFEST_TEXT)


def _build_wheel(tmp_path: Path, *, extra_files: dict[str, str] | None = None,
                 omit: set[str] | None = None, version: str = _VERSION) -> Path:
    """Create a minimal synthetic .whl with all required entries derived from manifests."""
    whl = tmp_path / "fake.whl"
    omit = omit or set()
    files: dict[str, str] = {}

    # Core files
    for f in mod._CORE_REQUIRED_FILES:
        if f in omit:
            continue
        if f == "kanon/__init__.py":
            files[f] = f'__version__ = "{version}"\n'
        elif f == "kanon/kit/manifest.yaml":
            files[f] = _TOP_MANIFEST_TEXT
        else:
            files[f] = ""

    # Aspect files derived from manifests (same logic the script uses)
    for _name, entry in _TOP_MANIFEST["aspects"].items():
        aspect_base = "kanon/kit/" + entry["path"]
        sub_path = _KIT / entry["path"] / "manifest.yaml"
        sub_text = sub_path.read_text(encoding="utf-8")
        sub = yaml.safe_load(sub_text)

        mf = f"{aspect_base}/manifest.yaml"
        if mf not in omit:
            files[mf] = sub_text

        rng = entry["depth-range"]
        for d in range(int(rng[0]), int(rng[1]) + 1):
            depth_entry = sub.get(f"depth-{d}", {})
            if not isinstance(depth_entry, dict):
                continue
            amd = f"{aspect_base}/agents-md/depth-{d}.md"
            if amd not in omit:
                files[amd] = ""
            for rel in depth_entry.get("files", []) or []:
                fp = f"{aspect_base}/files/{rel}"
                if fp not in omit:
                    files[fp] = ""
            for rel in depth_entry.get("protocols", []) or []:
                fp = f"{aspect_base}/protocols/{rel}"
                if fp not in omit:
                    files[fp] = ""
            for sec in depth_entry.get("sections", []) or []:
                if sec == "protocols-index":
                    continue
                fp = f"{aspect_base}/sections/{sec}.md"
                if fp not in omit:
                    files[fp] = ""

    if extra_files:
        files.update(extra_files)

    # Changelog for version concordance
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        f"# Changelog\n\n## [{version}] \u2014 2025-01-01\n\n- Initial\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(whl, "w") as z:
        for fname, content in files.items():
            z.writestr(fname, content)
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
