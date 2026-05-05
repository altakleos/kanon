"""Tests for scripts/check_kit_consistency.py against the real repo.

Per plan T1 + T5: the gate's data source is now `pyproject.toml`'s
`[project.entry-points."kanon.aspects"]` table + each aspect's per-aspect
`manifest.yaml` (canonical per ADR-0055). Fixtures synthesize that layout
via the `_make_synthetic_aspect_bundle` helper, not the legacy kit YAML.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture(scope="module")
def ckc(load_ci_script):
    return load_ci_script("check_kit_consistency.py")


def test_real_repo_passes(ckc) -> None:
    """The kanon repo itself must satisfy kit-consistency invariants."""
    errors = ckc.run_checks()
    assert errors == [], "kit-consistency check failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(ckc, capsys: pytest.CaptureFixture[str]) -> None:
    rc = ckc.main([])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


# --- Fixture helper (plan T5) ---


def _make_synthetic_aspect_bundle(
    tmp_path: Path,
    aspects: dict[str, dict[str, Any]],
    *,
    extra_pyproject_text: str = "",
) -> Path:
    """Synthesize a minimal repo layout the new pyproject-as-oracle gate reads.

    Per plan T5: replaces the legacy `_make_minimal_kit` (which wrote the
    retired kit YAML). Creates:

    - ``<tmp_path>/pyproject.toml`` with a ``[project.entry-points."kanon.aspects"]``
      table listing each slug (mapped to a fake module path; the gate doesn't
      import them).
    - ``<tmp_path>/packages/kanon-aspects/src/kanon_aspects/aspects/<slug_dir>/manifest.yaml``
      per slug, populated with the supplied per-aspect manifest fields plus
      minimal ``depth-N`` stubs spanning the given ``depth-range``.
    - ``<tmp_path>/packages/kanon-core/src/kanon_core/kit/harnesses.yaml`` stub
      (the gate still reads this for ``_check_harnesses_yaml``).

    *aspects* maps slug → per-aspect manifest fields (e.g. ``stability``,
    ``depth-range``, ``default-depth``, ``requires``, ``provides``,
    ``byte-equality``, ``depth-N`` overrides).

    Returns ``tmp_path`` so tests can monkeypatch ``_REPO_ROOT`` and add
    further fixturing (extra files, agents-md templates, divergent
    byte-equality counterparts).
    """
    # 1. pyproject.toml with the entry-points table.
    entries = "\n".join(
        f'{slug} = "kanon_aspects.aspects.{slug.replace("-", "_")}.loader:MANIFEST"'
        for slug in aspects
    )
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "synthetic"\n\n'
        f'[project.entry-points."kanon.aspects"]\n{entries}\n'
        f"{extra_pyproject_text}",
        encoding="utf-8",
    )

    # 2. Per-aspect manifests under packages/kanon-aspects/src/kanon_aspects/aspects/<dir>/.
    aspects_pkg = tmp_path / "packages" / "kanon-aspects" / "src" / "kanon_aspects" / "aspects"
    for slug, fields in aspects.items():
        bundle = aspects_pkg / slug.replace("-", "_")
        bundle.mkdir(parents=True, exist_ok=True)
        # Default minimal manifest; caller's fields override.
        manifest: dict[str, Any] = {
            "stability": "stable",
            "depth-range": [0, 1],
            "default-depth": 1,
            "requires": [],
            "provides": [],
            "suggests": [],
        }
        manifest.update(fields)
        # Synthesize depth-N stubs for the declared depth-range so
        # _check_registry_and_manifests can resolve them. Caller-supplied
        # `depth-N` overrides win.
        rng = manifest.get("depth-range", [0, 1])
        if isinstance(rng, list) and len(rng) == 2:
            for d in range(int(rng[0]), int(rng[1]) + 1):
                manifest.setdefault(f"depth-{d}", {"files": [], "protocols": [], "sections": []})
        (bundle / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False),
            encoding="utf-8",
        )

    # 3. kit/harnesses.yaml stub for _check_harnesses_yaml.
    kit = tmp_path / "packages" / "kanon-core" / "src" / "kanon_core" / "kit"
    kit.mkdir(parents=True, exist_ok=True)
    (kit / "harnesses.yaml").write_text(
        "- name: test\n  path: TEST.md\n  body: Read AGENTS.md\n",
        encoding="utf-8",
    )
    return tmp_path


def _patch_paths(monkeypatch: pytest.MonkeyPatch, ckc, tmp_path: Path) -> None:
    """Monkeypatch the gate's three path constants to point at *tmp_path*.

    Per plan T9 (publisher-symmetry parameterization): the gate carries
    `_REPO_ROOT`, `_KIT`, and `_ASPECTS_PKG_ROOT` as module-level constants.
    Tests targeting any of the gate's checks must monkeypatch all three so
    the gate reads the synthetic fixture under tmp_path instead of the
    live repo.
    """
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        ckc, "_KIT",
        tmp_path / "packages" / "kanon-core" / "src" / "kanon_core" / "kit",
    )
    monkeypatch.setattr(
        ckc, "_ASPECTS_PKG_ROOT",
        tmp_path / "packages" / "kanon-aspects" / "src" / "kanon_aspects",
    )


def test_byte_equality_drift_detected(ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Byte-equality check catches divergent files."""
    _make_synthetic_aspect_bundle(
        tmp_path,
        {
            "kanon-sdd": {
                "byte-equality": [{"kit": "doc.md", "repo": "docs/doc.md"}],
            },
        },
    )
    _patch_paths(monkeypatch, ckc, tmp_path)
    # Create divergent kit-side and repo-canonical files
    bundle = tmp_path / "packages" / "kanon-aspects" / "src" / "kanon_aspects" / "aspects" / "kanon_sdd"
    (bundle / "files").mkdir()
    (bundle / "files" / "doc.md").write_text("kit version", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "doc.md").write_text("repo version", encoding="utf-8")

    errors: list[str] = []
    ckc._check_byte_equality(errors)
    assert len(errors) == 1
    assert "byte-equality drift" in errors[0]


# Phase A.3: test_missing_kit_md_detected and test_kit_md_bad_heading_detected
# retired with the gate's _check_kit_md_exists() function (per ADR-0048
# de-opinionation; kit.md template deleted).


def test_registry_bad_stability_detected(ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid stability value in per-aspect manifest is caught."""
    _make_synthetic_aspect_bundle(
        tmp_path,
        {"kanon-sdd": {"stability": "banana"}},
    )
    _patch_paths(monkeypatch, ckc, tmp_path)

    errors: list[str] = []
    ckc._check_registry_and_manifests(errors)
    assert any("invalid value" in e and "banana" in e for e in errors), (
        f"expected stability error, got: {errors}"
    )


def test_cross_aspect_ownership_conflict_detected(
    ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two aspects scaffolding the same file is caught."""
    _make_synthetic_aspect_bundle(
        tmp_path,
        {
            "kanon-sdd": {
                "depth-0": {"files": ["shared.md"], "protocols": [], "sections": []},
                "depth-1": {"files": [], "protocols": [], "sections": []},
            },
            "kanon-other": {
                "depth-range": [0, 0],
                "default-depth": 0,
                "stability": "experimental",
                "depth-0": {"files": ["shared.md"], "protocols": [], "sections": []},
            },
        },
    )
    _patch_paths(monkeypatch, ckc, tmp_path)

    # Create the files so bundle resolution + sub-manifest reads succeed.
    aspects_pkg = tmp_path / "packages" / "kanon-aspects" / "src" / "kanon_aspects" / "aspects"
    for slug_dir in ("kanon_sdd", "kanon_other"):
        files_dir = aspects_pkg / slug_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        (files_dir / "shared.md").write_text("x", encoding="utf-8")

    errors: list[str] = []
    ckc._check_cross_aspect_exclusivity(errors)
    assert len(errors) == 1
    assert "ownership conflict" in errors[0]
    assert "shared.md" in errors[0]


def test_marker_imbalance_detected(ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unbalanced begin/end markers in agents-md templates are caught."""
    _make_synthetic_aspect_bundle(tmp_path, {"kanon-sdd": {}})
    _patch_paths(monkeypatch, ckc, tmp_path)
    bundle = tmp_path / "packages" / "kanon-aspects" / "src" / "kanon_aspects" / "aspects" / "kanon_sdd"
    agents_md_dir = bundle / "agents-md"
    agents_md_dir.mkdir()
    (agents_md_dir / "depth-0.md").write_text(
        "<!-- kanon:begin:kanon-sdd/body -->\nContent\n",  # missing end marker
        encoding="utf-8",
    )

    errors: list[str] = []
    ckc._check_agents_md_markers(errors)
    assert len(errors) == 1
    assert "imbalance" in errors[0]


def test_harnesses_yaml_missing_field_detected(
    ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Harness entry missing required field is caught."""
    _make_synthetic_aspect_bundle(tmp_path, {"kanon-sdd": {}})
    kit = tmp_path / "packages" / "kanon-core" / "src" / "kanon_core" / "kit"
    (kit / "harnesses.yaml").write_text(
        "- name: broken\n  path: TEST.md\n",  # missing 'body'
        encoding="utf-8",
    )
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ckc, "_KIT", kit)

    errors: list[str] = []
    ckc._check_harnesses_yaml(errors)
    assert len(errors) == 1
    assert "missing required field" in errors[0]
    assert "body" in errors[0]


# --- ADR-0028: namespace-ownership tests (T13) ---


def test_kit_aspect_with_project_prefix_rejected(
    ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `project-` aspect declared via the kit's pyproject entry-points table
    is rejected at gate time (ADR-0028 namespace ownership).

    The kit's CI hard-fails when a `kanon.aspects` entry-point declares a
    slug outside the `kanon-` namespace; project-aspects must instead live
    in the consumer's `.kanon/aspects/` per ADR-0028.
    """
    _make_synthetic_aspect_bundle(
        tmp_path,
        {"project-misnamed": {"stability": "experimental"}},
    )
    _patch_paths(monkeypatch, ckc, tmp_path)

    errors: list[str] = []
    ckc._check_registry_and_manifests(errors)
    assert any(
        "kit-side aspect names must" in e and "project-misnamed" in e for e in errors
    ), f"expected ADR-0028 namespace-ownership error, got: {errors}"


def test_kit_aspect_with_bare_name_rejected(
    ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare (unprefixed) aspect declared via the kit's pyproject entry-points
    table is rejected (ADR-0028).

    The bare-name shorthand is for CLI input only; in the kit registry, every
    aspect must carry the `kanon-` prefix.
    """
    _make_synthetic_aspect_bundle(tmp_path, {"sdd": {}})
    _patch_paths(monkeypatch, ckc, tmp_path)

    errors: list[str] = []
    ckc._check_registry_and_manifests(errors)
    assert any(
        "kit-side aspect names must" in e and "'sdd'" in e for e in errors
    ), f"expected ADR-0028 namespace-ownership error, got: {errors}"
