"""Tests for ci/check_kit_consistency.py against the real repo."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


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


# --- Synthetic failure tests ---


def _make_minimal_kit(tmp_path: Path) -> Path:
    """Create a minimal valid kit structure for testing individual checks."""
    kit = tmp_path / "src" / "kanon" / "kit"
    kit.mkdir(parents=True)
    # Top-level manifest with one aspect
    (kit / "manifest.yaml").write_text(
        "aspects:\n"
        "  kanon-sdd:\n"
        "    path: aspects/kanon-sdd\n"
        "    stability: stable\n"
        "    depth-range: [0, 1]\n"
        "    default-depth: 1\n",
        encoding="utf-8",
    )
    # Aspect sub-manifest
    sdd = kit / "aspects" / "kanon-sdd"
    sdd.mkdir(parents=True)
    (sdd / "manifest.yaml").write_text(
        "depth-0:\n  files: []\n  sections: []\ndepth-1:\n  files: []\n  sections: []\n",
        encoding="utf-8",
    )
    # kit.md
    (kit / "kit.md").write_text("# Kit\nMinimal.\n", encoding="utf-8")
    # harnesses.yaml
    (kit / "harnesses.yaml").write_text(
        "- name: test\n  path: TEST.md\n  body: Read AGENTS.md\n",
        encoding="utf-8",
    )
    return kit


def test_byte_equality_drift_detected(ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Byte-equality check catches divergent files."""
    kit = _make_minimal_kit(tmp_path)
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)
    # Add byte-equality entry to sub-manifest
    sdd = kit / "aspects" / "kanon-sdd"
    (sdd / "manifest.yaml").write_text(
        "byte-equality:\n"
        "  - kit: doc.md\n"
        "    repo: docs/doc.md\n"
        "depth-0:\n  files: []\n  sections: []\n"
        "depth-1:\n  files: []\n  sections: []\n",
        encoding="utf-8",
    )
    # Create divergent files
    (sdd / "files").mkdir(exist_ok=True)
    (sdd / "files" / "doc.md").write_text("kit version", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "doc.md").write_text("repo version", encoding="utf-8")

    errors: list[str] = []
    ckc._check_byte_equality(errors)
    assert len(errors) == 1
    assert "byte-equality drift" in errors[0]


def test_missing_kit_md_detected(ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing kit.md is caught."""
    kit = _make_minimal_kit(tmp_path)
    (kit / "kit.md").unlink()
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_kit_md_exists(errors)
    assert len(errors) == 1
    assert "missing kernel doc" in errors[0]


def test_kit_md_bad_heading_detected(ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """kit.md without a top-level heading is caught."""
    kit = _make_minimal_kit(tmp_path)
    (kit / "kit.md").write_text("No heading here.\n", encoding="utf-8")
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_kit_md_exists(errors)
    assert len(errors) == 1
    assert "expected top-level" in errors[0]


def test_registry_bad_stability_detected(ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid stability value is caught."""
    kit = _make_minimal_kit(tmp_path)
    (kit / "manifest.yaml").write_text(
        "aspects:\n"
        "  kanon-sdd:\n"
        "    path: aspects/kanon-sdd\n"
        "    stability: banana\n"
        "    depth-range: [0, 1]\n"
        "    default-depth: 1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_registry_and_manifests(errors)
    assert any("invalid value" in e and "banana" in e for e in errors)


def test_cross_aspect_ownership_conflict_detected(
    ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two aspects scaffolding the same file is caught."""
    kit = _make_minimal_kit(tmp_path)
    # Add a second aspect that scaffolds the same file as sdd
    (kit / "manifest.yaml").write_text(
        "aspects:\n"
        "  sdd:\n"
        "    path: aspects/kanon-sdd\n"
        "    stability: stable\n"
        "    depth-range: [0, 1]\n"
        "    default-depth: 1\n"
        "  other:\n"
        "    path: aspects/other\n"
        "    stability: experimental\n"
        "    depth-range: [0, 0]\n"
        "    default-depth: 0\n",
        encoding="utf-8",
    )
    other = kit / "aspects" / "other"
    other.mkdir(parents=True)
    (other / "manifest.yaml").write_text(
        "depth-0:\n  files:\n    - shared.md\n  sections: []\n",
        encoding="utf-8",
    )
    # sdd also scaffolds shared.md
    (kit / "aspects" / "kanon-sdd" / "manifest.yaml").write_text(
        "depth-0:\n  files:\n    - shared.md\n  sections: []\n"
        "depth-1:\n  files: []\n  sections: []\n",
        encoding="utf-8",
    )
    # Create the files so path resolution doesn't fail
    (kit / "aspects" / "kanon-sdd" / "files").mkdir(exist_ok=True)
    (kit / "aspects" / "kanon-sdd" / "files" / "shared.md").write_text("x", encoding="utf-8")
    (other / "files").mkdir()
    (other / "files" / "shared.md").write_text("x", encoding="utf-8")

    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_cross_aspect_exclusivity(errors)
    assert len(errors) == 1
    assert "ownership conflict" in errors[0]
    assert "shared.md" in errors[0]


def test_marker_imbalance_detected(ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unbalanced begin/end markers in agents-md templates are caught."""
    kit = _make_minimal_kit(tmp_path)
    agents_md_dir = kit / "aspects" / "kanon-sdd" / "agents-md"
    agents_md_dir.mkdir()
    (agents_md_dir / "depth-0.md").write_text(
        "<!-- kanon:begin:kanon-sdd/body -->\nContent\n",  # missing end marker
        encoding="utf-8",
    )
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_agents_md_markers(errors)
    assert len(errors) == 1
    assert "imbalance" in errors[0]


def test_harnesses_yaml_missing_field_detected(
    ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Harness entry missing required field is caught."""
    kit = _make_minimal_kit(tmp_path)
    (kit / "harnesses.yaml").write_text(
        "- name: broken\n  path: TEST.md\n",  # missing 'body'
        encoding="utf-8",
    )
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_harnesses_yaml(errors)
    assert len(errors) == 1
    assert "missing required field" in errors[0]
    assert "body" in errors[0]


# --- ADR-0028: namespace-ownership tests (T13) ---


def test_kit_aspect_with_project_prefix_rejected(
    ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A kit-side directory may not declare a `project-` aspect (ADR-0028).

    The kit's CI hard-fails when an aspect-name is outside the `kanon-` namespace.
    """
    kit = tmp_path / "src" / "kanon" / "kit"
    kit.mkdir(parents=True)
    (kit / "manifest.yaml").write_text(
        "aspects:\n"
        "  project-misnamed:\n"
        "    path: aspects/project-misnamed\n"
        "    stability: experimental\n"
        "    depth-range: [0, 1]\n"
        "    default-depth: 1\n",
        encoding="utf-8",
    )
    (kit / "aspects" / "project-misnamed").mkdir(parents=True)
    (kit / "aspects" / "project-misnamed" / "manifest.yaml").write_text(
        "depth-0:\n  files: []\n  sections: []\ndepth-1:\n  files: []\n  sections: []\n",
        encoding="utf-8",
    )
    (kit / "kit.md").write_text("# Kit\nMinimal.\n", encoding="utf-8")
    (kit / "harnesses.yaml").write_text(
        "- name: test\n  path: TEST.md\n  body: Read AGENTS.md\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_registry_and_manifests(errors)
    assert any(
        "kit-side aspect names must" in e and "project-misnamed" in e for e in errors
    ), f"expected ADR-0028 namespace-ownership error, got: {errors}"


def test_kit_aspect_with_bare_name_rejected(
    ckc, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A kit-side directory may not declare a bare (unprefixed) aspect (ADR-0028).

    The bare-name shorthand is for CLI input only; in the kit registry, every
    aspect must carry the `kanon-` prefix.
    """
    kit = tmp_path / "src" / "kanon" / "kit"
    kit.mkdir(parents=True)
    (kit / "manifest.yaml").write_text(
        "aspects:\n"
        "  sdd:\n"  # bare, no `kanon-` prefix
        "    path: aspects/kanon-sdd\n"
        "    stability: stable\n"
        "    depth-range: [0, 1]\n"
        "    default-depth: 1\n",
        encoding="utf-8",
    )
    (kit / "aspects" / "kanon-sdd").mkdir(parents=True)
    (kit / "aspects" / "kanon-sdd" / "manifest.yaml").write_text(
        "depth-0:\n  files: []\n  sections: []\ndepth-1:\n  files: []\n  sections: []\n",
        encoding="utf-8",
    )
    (kit / "kit.md").write_text("# Kit\nMinimal.\n", encoding="utf-8")
    (kit / "harnesses.yaml").write_text(
        "- name: test\n  path: TEST.md\n  body: Read AGENTS.md\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_registry_and_manifests(errors)
    assert any(
        "kit-side aspect names must" in e and "'sdd'" in e for e in errors
    ), f"expected ADR-0028 namespace-ownership error, got: {errors}"
