"""Tests for validator error branches in kanon._verify."""
from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from kanon.cli import main


def _init_project(tmp_path: Path) -> Path:
    """Init a tier-1 project and return its path."""
    runner = CliRunner()
    target = tmp_path / "proj"
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output
    return target


def _add_project_aspect(target: Path, aspect_name: str, validators: list[str]) -> None:
    """Register a project-aspect with given validators in config and manifest."""
    # Update config to include the project-aspect
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["aspects"][aspect_name] = {"depth": 1, "enabled_at": "2026-01-01", "config": {}}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    # Create the project-aspect manifest
    aspect_dir = target / ".kanon" / "aspects" / aspect_name
    aspect_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "stability": "experimental",
        "depth-range": [0, 1],
        "default-depth": 1,
        "validators": validators,
        "depth-0": {},
        "depth-1": {},
    }
    (aspect_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )


def test_project_validator_import_error(tmp_path: Path) -> None:
    """Verify reports error when a project-validator module cannot be imported."""
    target = _init_project(tmp_path)
    _add_project_aspect(target, "project-test", ["nonexistent_module"])

    runner = CliRunner()
    result = runner.invoke(main, ["verify", str(target)])
    assert "import failed" in result.output


def test_project_validator_missing_check(tmp_path: Path) -> None:
    """Verify reports error when a project-validator has no check() callable."""
    target = _init_project(tmp_path)
    _add_project_aspect(target, "project-test", ["_vv_no_check_mod"])

    # Create the module without a check() function
    mod_file = target / "_vv_no_check_mod.py"
    mod_file.write_text("# No check function here\nVALUE = 42\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["verify", str(target)])
    assert "no callable `check`" in result.output or "no callable `check(" in result.output


def test_project_validator_runtime_exception(tmp_path: Path) -> None:
    """Verify reports error when a project-validator's check() raises."""
    target = _init_project(tmp_path)
    _add_project_aspect(target, "project-test", ["_vv_bad_check_mod"])

    # Create a module whose check() raises
    mod_file = target / "_vv_bad_check_mod.py"
    mod_file.write_text(
        "from pathlib import Path\n"
        "def check(target: Path, errors: list, warnings: list) -> None:\n"
        "    raise RuntimeError('validator boom')\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(main, ["verify", str(target)])
    assert "RuntimeError" in result.output
    assert "validator boom" in result.output


def test_kit_validator_lookup_failure_warns(tmp_path: Path) -> None:
    """Kit validator lookup failure surfaces as a warning, not silent."""
    from unittest.mock import patch

    from kanon._verify import run_kit_validators

    errors: list[str] = []
    warnings: list[str] = []
    with patch(
        "kanon._verify._aspect_depth_validators",
        side_effect=RuntimeError("boom"),
    ):
        run_kit_validators(tmp_path, {"kanon-sdd": 1}, errors, warnings)
    assert any("kit-validator lookup failed" in w for w in warnings)


def test_fidelity_capability_lookup_failure_warns(tmp_path: Path) -> None:
    """Fidelity capability lookup failure surfaces as a warning, not silent."""
    from unittest.mock import patch

    from kanon._verify import check_fidelity_assertions

    errors: list[str] = []
    warnings: list[str] = []
    with patch(
        "kanon._verify._aspect_provides",
        side_effect=RuntimeError("boom"),
    ):
        check_fidelity_assertions(tmp_path, {"kanon-sdd": 1}, errors, warnings)
    assert any("capability lookup failed" in w for w in warnings)
