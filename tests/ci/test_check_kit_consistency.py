"""Tests for ci/check_kit_consistency.py against the real repo."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VALIDATOR_PATH = _REPO_ROOT / "ci" / "check_kit_consistency.py"
assert _VALIDATOR_PATH.is_file(), f"validator not found: {_VALIDATOR_PATH}"


def _load_validator():
    spec = importlib.util.spec_from_file_location("check_kit_consistency", _VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


ckc = _load_validator()


def test_real_repo_passes() -> None:
    """The kanon repo itself must satisfy kit-consistency invariants."""
    errors = ckc.run_checks()
    assert errors == [], "kit-consistency check failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(capsys: pytest.CaptureFixture[str]) -> None:
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
        "  sdd:\n"
        "    path: aspects/sdd\n"
        "    stability: stable\n"
        "    depth-range: [0, 1]\n"
        "    default-depth: 1\n",
        encoding="utf-8",
    )
    # Aspect sub-manifest
    sdd = kit / "aspects" / "sdd"
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


def test_byte_equality_drift_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Byte-equality check catches divergent files."""
    kit = _make_minimal_kit(tmp_path)
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)
    # Add byte-equality entry to sub-manifest
    sdd = kit / "aspects" / "sdd"
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


def test_missing_kit_md_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing kit.md is caught."""
    kit = _make_minimal_kit(tmp_path)
    (kit / "kit.md").unlink()
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_kit_md_exists(errors)
    assert len(errors) == 1
    assert "missing kernel doc" in errors[0]


def test_kit_md_bad_heading_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """kit.md without a top-level heading is caught."""
    kit = _make_minimal_kit(tmp_path)
    (kit / "kit.md").write_text("No heading here.\n", encoding="utf-8")
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_kit_md_exists(errors)
    assert len(errors) == 1
    assert "expected top-level" in errors[0]


def test_registry_bad_stability_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid stability value is caught."""
    kit = _make_minimal_kit(tmp_path)
    (kit / "manifest.yaml").write_text(
        "aspects:\n"
        "  sdd:\n"
        "    path: aspects/sdd\n"
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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two aspects scaffolding the same file is caught."""
    kit = _make_minimal_kit(tmp_path)
    # Add a second aspect that scaffolds the same file as sdd
    (kit / "manifest.yaml").write_text(
        "aspects:\n"
        "  sdd:\n"
        "    path: aspects/sdd\n"
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
    (kit / "aspects" / "sdd" / "manifest.yaml").write_text(
        "depth-0:\n  files:\n    - shared.md\n  sections: []\n"
        "depth-1:\n  files: []\n  sections: []\n",
        encoding="utf-8",
    )
    # Create the files so path resolution doesn't fail
    (kit / "aspects" / "sdd" / "files").mkdir(exist_ok=True)
    (kit / "aspects" / "sdd" / "files" / "shared.md").write_text("x", encoding="utf-8")
    (other / "files").mkdir()
    (other / "files" / "shared.md").write_text("x", encoding="utf-8")

    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_cross_aspect_exclusivity(errors)
    assert len(errors) == 1
    assert "ownership conflict" in errors[0]
    assert "shared.md" in errors[0]


def test_marker_imbalance_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unbalanced begin/end markers in agents-md templates are caught."""
    kit = _make_minimal_kit(tmp_path)
    agents_md_dir = kit / "aspects" / "sdd" / "agents-md"
    agents_md_dir.mkdir()
    (agents_md_dir / "depth-0.md").write_text(
        "<!-- kanon:begin:sdd/body -->\nContent\n",  # missing end marker
        encoding="utf-8",
    )
    monkeypatch.setattr(ckc, "_KIT", kit)
    monkeypatch.setattr(ckc, "_REPO_ROOT", tmp_path)

    errors: list[str] = []
    ckc._check_agents_md_markers(errors)
    assert len(errors) == 1
    assert "imbalance" in errors[0]


def test_harnesses_yaml_missing_field_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
