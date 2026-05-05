"""Tests for scripts/check_package_contents.py."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import yaml

# This file needs module-level access to the loaded module (for _build_wheel),
# so we call the conftest loader directly rather than using a fixture.
from conftest import REPO_ROOT as _REPO_ROOT  # noqa: E402
from conftest import _load_ci_script  # noqa: E402

mod = _load_ci_script("check_package_contents.py")

_TAG = "v1.0.0"
_VERSION = "1.0.0"

# Per plan T2 + T4: the gate's source-of-truth for aspect enumeration is
# pyproject.toml's `[project.entry-points."kanon.aspects"]` table (mirrored
# in the wheel's `<dist-info>/entry_points.txt`). The kit YAML at
# `kanon_core/kit/manifest.yaml` is retired in T4; tests therefore enumerate
# slugs from pyproject directly, not from the retired YAML.
_PYPROJECT_TEXT = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
_REF_DATA = _REPO_ROOT / "packages" / "kanon-aspects" / "src" / "kanon_aspects" / "aspects"


def _aspect_slugs_from_pyproject() -> list[str]:
    """Return aspect slugs from pyproject's `kanon.aspects` entry-point table.

    Mirrors `scripts/check_kit_consistency.py:_extract_aspect_slugs_from_pyproject`
    so tests stay aligned with the gate's own source-of-truth.
    """
    header = re.compile(
        r'^\s*\[project\.entry-points\."kanon\.aspects"\]\s*$', re.MULTILINE,
    )
    kv = re.compile(
        r'^\s*(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"(?P<value>[^"]+)"\s*(?:#.*)?$'
    )
    match = header.search(_PYPROJECT_TEXT)
    assert match is not None, "pyproject missing [project.entry-points.\"kanon.aspects\"]"
    rest = _PYPROJECT_TEXT[match.end():]
    next_section = re.search(r"^\s*\[", rest, re.MULTILINE)
    body = rest[: next_section.start()] if next_section else rest
    slugs: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = kv.match(line)
        if m is not None:
            slugs.append(m.group("key"))
    return sorted(slugs)


def _build_wheel(tmp_path: Path, *, extra_files: dict[str, str] | None = None,
                 omit: set[str] | None = None, version: str = _VERSION) -> Path:
    """Create a minimal synthetic .whl with all required entries.

    Per plan T2: the wheel must include `<dist-info>/entry_points.txt` with the
    `[kanon.aspects]` section listing each slug — that file is the gate's
    external oracle for aspect enumeration (replacing the retired
    `kanon_core/kit/manifest.yaml`).
    """
    whl = tmp_path / "fake.whl"
    omit = omit or set()
    files: dict[str, str] = {}

    # Core files
    for f in mod._CORE_REQUIRED_FILES:
        if f in omit:
            continue
        if f == "kanon_core/__init__.py":
            files[f] = f'__version__ = "{version}"\n'
        else:
            files[f] = ""

    # entry_points.txt (gate's external oracle per T2). The dist-info dir
    # name here is illustrative; the gate matches any "*.dist-info/entry_points.txt".
    slugs = _aspect_slugs_from_pyproject()
    dist_info_dir = f"kanon_kit-{version}.dist-info"
    ep_lines = ["[kanon.aspects]"]
    for slug in slugs:
        ep_lines.append(f"{slug} = kanon_aspects.aspects.{slug.replace('-', '_')}.loader:MANIFEST")
    files[f"{dist_info_dir}/entry_points.txt"] = "\n".join(ep_lines) + "\n"

    for _name in slugs:
        _dir_name = _name.replace("-", "_")
        aspect_base = f"kanon_aspects/aspects/{_dir_name}"
        sub_path = _REF_DATA / _dir_name / "manifest.yaml"
        sub_text = sub_path.read_text(encoding="utf-8")
        sub = yaml.safe_load(sub_text)
        entry = {"depth-range": sub.get("depth-range", [0, 0])}

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
    whl = _build_wheel(tmp_path, omit={"kanon_core/__init__.py"})
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


# --- Phase A.3: kit-globals deletion. kit.md was retired and is no longer ---
# --- in the wheel; the gate must not require it. ---


def test_kit_md_not_in_core_required_files() -> None:
    """Per Phase A.3 (kit-globals deletion), kernel/kit/kit.md was retired.
    The wheel-shape gate must not require it — otherwise the v0.4.0a1
    release-preflight against the built wheel will hard-block the tag."""
    assert "kanon_core/kit/kit.md" not in mod._CORE_REQUIRED_FILES
