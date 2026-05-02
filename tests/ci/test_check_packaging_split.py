"""Tests for ci/check_packaging_split.py — Phase A.1 packaging-split gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def cps(load_ci_script):
    return load_ci_script("check_packaging_split.py")


def test_real_repo_passes(cps) -> None:
    """The kanon repo's three packaging skeletons must satisfy the gate."""
    errors = cps.run_checks()
    assert errors == [], "packaging-split check failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(cps, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cps.main([])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"
    assert parsed["errors"] == []


# --- Synthetic failure tests ---


def _seed_packaging(tmp_path: Path) -> Path:
    """Create a minimal three-file packaging skeleton matching the canonical shape."""
    pkg = tmp_path / "packaging"
    (pkg / "substrate").mkdir(parents=True)
    (pkg / "reference").mkdir(parents=True)
    (pkg / "kit").mkdir(parents=True)
    (pkg / "substrate" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-substrate"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["click>=8.1", "pyyaml>=6.0"]\n'
        '[project.scripts]\n'
        'kanon = "kanon.cli:main"\n'
        '[tool.hatch.build.targets.wheel]\n'
        'exclude = ["../../src/kanon/kit/aspects/**"]\n',
        encoding="utf-8",
    )
    (pkg / "reference" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-reference"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["kanon-substrate==1.0.0a1"]\n'
        '[project.entry-points."kanon.aspects"]\n'
        'kanon-deps = "kanon_reference.aspects.kanon_deps:MANIFEST"\n'
        'kanon-fidelity = "kanon_reference.aspects.kanon_fidelity:MANIFEST"\n'
        'kanon-release = "kanon_reference.aspects.kanon_release:MANIFEST"\n'
        'kanon-sdd = "kanon_reference.aspects.kanon_sdd:MANIFEST"\n'
        'kanon-security = "kanon_reference.aspects.kanon_security:MANIFEST"\n'
        'kanon-testing = "kanon_reference.aspects.kanon_testing:MANIFEST"\n'
        'kanon-worktrees = "kanon_reference.aspects.kanon_worktrees:MANIFEST"\n',
        encoding="utf-8",
    )
    (pkg / "kit" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-kit"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["kanon-substrate==1.0.0a1", "kanon-reference==1.0.0a1"]\n',
        encoding="utf-8",
    )
    return pkg


def test_substrate_missing_file_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing substrate pyproject is caught as a missing-file error."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "substrate" / "pyproject.toml").unlink()
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("missing: packaging/substrate/pyproject.toml" in e for e in errors)


def test_substrate_invalid_toml_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Garbage TOML in any of the three files surfaces a parse error."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "reference" / "pyproject.toml").write_text("not = valid = toml\n", encoding="utf-8")
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("invalid TOML" in e and "reference" in e for e in errors)


def test_substrate_wrong_name_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Substrate's [project].name must be 'kanon-substrate'."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "substrate" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "wrong-name"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["click>=8.1", "pyyaml>=6.0"]\n'
        '[project.scripts]\n'
        'kanon = "kanon.cli:main"\n'
        '[tool.hatch.build.targets.wheel]\n'
        'exclude = ["../../src/kanon/kit/aspects/**"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("must be 'kanon-substrate'" in e for e in errors)


def test_substrate_wrong_version_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Substrate's [project].version must be 1.0.0a1."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "substrate" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-substrate"\n'
        'version = "0.9.9"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["click>=8.1", "pyyaml>=6.0"]\n'
        '[project.scripts]\n'
        'kanon = "kanon.cli:main"\n'
        '[tool.hatch.build.targets.wheel]\n'
        'exclude = ["../../src/kanon/kit/aspects/**"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("[project].version must be '1.0.0a1'" in e for e in errors)


def test_substrate_missing_exclude_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Substrate's wheel.exclude must contain '../../src/kanon/kit/aspects/**'."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "substrate" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-substrate"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["click>=8.1", "pyyaml>=6.0"]\n'
        '[project.scripts]\n'
        'kanon = "kanon.cli:main"\n'
        '[tool.hatch.build.targets.wheel]\n'
        'exclude = []\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("must contain" in e and "kit/aspects/**" in e for e in errors)


def test_substrate_missing_dep_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Substrate must depend on click and pyyaml."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "substrate" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-substrate"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = []\n'
        '[project.scripts]\n'
        'kanon = "kanon.cli:main"\n'
        '[tool.hatch.build.targets.wheel]\n'
        'exclude = ["../../src/kanon/kit/aspects/**"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("missing required pin 'click>=8.1'" in e for e in errors)
    assert any("missing required pin 'pyyaml>=6.0'" in e for e in errors)


def test_substrate_wrong_scripts_entry_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[project.scripts].kanon must be 'kanon.cli:main'."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "substrate" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-substrate"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["click>=8.1", "pyyaml>=6.0"]\n'
        '[project.scripts]\n'
        'kanon = "wrong:entry"\n'
        '[tool.hatch.build.targets.wheel]\n'
        'exclude = ["../../src/kanon/kit/aspects/**"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("[project.scripts].kanon must be 'kanon.cli:main'" in e for e in errors)


def test_reference_missing_substrate_pin_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reference must pin kanon-substrate==1.0.0a1."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "reference" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-reference"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = []\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("must pin 'kanon-substrate==1.0.0a1'" in e for e in errors)


def test_kit_meta_missing_pins_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kit-meta must pin both substrate and reference."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "kit" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-kit"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = []\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("must pin 'kanon-substrate==1.0.0a1'" in e for e in errors)
    assert any("must pin 'kanon-reference==1.0.0a1'" in e for e in errors)


def test_reference_missing_entry_points_block_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase A.2.1: reference must declare the seven entry-points."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "reference" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-reference"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["kanon-substrate==1.0.0a1"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any(
        "missing entry 'kanon-sdd'" in e for e in errors
    ), f"expected missing-entry error, got {errors}"


def test_reference_wrong_entry_point_target_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase A.2.1: each entry-point must target kanon_reference.aspects.kanon_<id>:MANIFEST."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "reference" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "kanon-reference"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["kanon-substrate==1.0.0a1"]\n'
        '[project.entry-points."kanon.aspects"]\n'
        'kanon-deps = "wrong.target:LOADER"\n'
        'kanon-fidelity = "kanon_reference.aspects.kanon_fidelity:MANIFEST"\n'
        'kanon-release = "kanon_reference.aspects.kanon_release:MANIFEST"\n'
        'kanon-sdd = "kanon_reference.aspects.kanon_sdd:MANIFEST"\n'
        'kanon-security = "kanon_reference.aspects.kanon_security:MANIFEST"\n'
        'kanon-testing = "kanon_reference.aspects.kanon_testing:MANIFEST"\n'
        'kanon-worktrees = "kanon_reference.aspects.kanon_worktrees:MANIFEST"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any(
        "kanon-deps" in e and "wrong.target:LOADER" in e for e in errors
    ), f"expected wrong-target error, got {errors}"


def test_kit_meta_wrong_name_detected(
    cps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kit-meta's [project].name must be 'kanon-kit'."""
    pkg = _seed_packaging(tmp_path)
    (pkg / "kit" / "pyproject.toml").write_text(
        '[project]\n'
        'name = "wrong"\n'
        'version = "1.0.0a1"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["kanon-substrate==1.0.0a1", "kanon-reference==1.0.0a1"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cps, "_PACKAGING", pkg)

    errors = cps.run_checks()
    assert any("must be 'kanon-kit'" in e for e in errors)
